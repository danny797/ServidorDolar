from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# --- FUNCIÓN 1: BINANCE (P2P / PARALELO) ---
def consultar_binance(tipo_orden):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        
        payload = {
            "asset": "USDT",
            "fiat": "VES",
            "merchantCheck": False,
            "page": 1,
            "publisherType": None,
            "rows": 100,        
            "tradeType": tipo_orden, 
            "transAmount": "500"     
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        data = response.json()
        anuncios = data['data']
        
        if not anuncios: return 0.0

        suma = 0.0
        cantidad = 0
        
        for anuncio in anuncios:
            precio = float(anuncio['adv']['price'])
            suma += precio
            cantidad += 1
            
        return suma / cantidad if cantidad > 0 else 0.0

    except Exception as e:
        print(f"Error en {tipo_orden}: {e}")
        return 0.0

def obtener_promedio_mercado():
    promedio_venta_usdt = consultar_binance("BUY")
    promedio_compra_usdt = consultar_binance("SELL")
    
    if promedio_venta_usdt > 0 and promedio_compra_usdt > 0:
        return (promedio_venta_usdt + promedio_compra_usdt) / 2
    elif promedio_venta_usdt > 0:
        return promedio_venta_usdt
    else:
        return 0.0

# --- FUNCIÓN 2: SCRAPING BCV (DOLAR Y EURO JUNTOS) ---
def obtener_tasas_bcv():
    # Diccionario para guardar resultados. Si falla, quedan en 0.0
    resultados = {"dolar": 0.0, "euro": 0.0}
    
    try:
        url = "https://www.bcv.org.ve"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Hacemos UNA sola petición para no saturar al BCV
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Buscar Dólar (id="dolar")
        div_dolar = soup.find('div', {'id': 'dolar'})
        if div_dolar:
            texto = div_dolar.find('strong').text.strip()
            resultados["dolar"] = float(texto.replace(',', '.'))
            
        # 2. Buscar Euro (id="euro")
        div_euro = soup.find('div', {'id': 'euro'})
        if div_euro:
            texto = div_euro.find('strong').text.strip()
            resultados["euro"] = float(texto.replace(',', '.'))

        return resultados

    except Exception as e:
        print(f"Error raspando BCV: {e}")
        return resultados # Devuelve ceros si falla

@app.route('/tasas')
def tasas():
    # 1. Obtener tasas del BCV (Página Oficial)
    tasas_bcv = obtener_tasas_bcv()
    oficial_bcv = tasas_bcv["dolar"]
    euro_bcv = tasas_bcv["euro"]

    # 2. Obtener tasas de Binance (Mercado)
    paralelo_binance = obtener_promedio_mercado()
    
    # 3. Datos de Respaldo (DolarApi) por si el scraping falla
    try:
        datos_api = requests.get("https://ve.dolarapi.com/v1/dolares/oficial").json()
        oficial_api = datos_api["promedio"]
    except:
        oficial_api = 0.0

    # --- LÓGICA DE SELECCIÓN FINAL ---

    # A. Dólar Oficial: Preferimos scraping BCV, si falla (da 0), usamos API
    if oficial_bcv > 0:
        tasa_oficial_final = oficial_bcv
    else:
        tasa_oficial_final = oficial_api

    # B. Dólar Paralelo: Preferimos Binance, si falla, usamos API paralelo
    if paralelo_binance > 0:
        tasa_paralela_final = paralelo_binance
        fuente_usdt = "Binance P2P"
    else:
        try:
            tasa_paralela_final = requests.get("https://ve.dolarapi.com/v1/dolares/paralelo").json()["promedio"]
            fuente_usdt = "DolarApi (Respaldo)"
        except:
            tasa_paralela_final = 0.0
            fuente_usdt = "Error"

    # C. Euro: Preferimos scraping BCV, si falla, calculamos matemático
    if euro_bcv > 0:
        tasa_euro_final = euro_bcv
    else:
        try:
            # Cálculo matemático de emergencia
            factor = requests.get("https://open.er-api.com/v6/latest/EUR").json()["rates"]["USD"]
            tasa_euro_final = tasa_oficial_final * factor
        except:
            tasa_euro_final = 0.0

    return jsonify({
        "oficial": tasa_oficial_final, # Ahora viene directo del BCV
        "paralelo": tasa_paralela_final,
        "euro": tasa_euro_final,
        "fuente": fuente_usdt
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
