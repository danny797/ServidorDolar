from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# --- FUNCIÓN AUXILIAR PARA CONSULTAR UN LADO (COMPRA O VENTA) ---
def consultar_binance(tipo_orden):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        
        # tradeType "BUY" = Anuncios de gente vendiendo (Tú compras)
        # tradeType "SELL" = Anuncios de gente comprando (Tú vendes)
        payload = {
            "asset": "USDT",
            "fiat": "VES",
            "merchantCheck": False,
            "page": 1,
            "publisherType": None,
            "rows": 50,       
            "tradeType": tipo_orden, 
            "transAmount": "500"     # Filtro de 500 Bs para precios "de calle"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        data = response.json()
        
        anuncios = data['data']
        
        if not anuncios:
            return 0.0

        suma = 0.0
        cantidad = 0
        
        # Promediamos todos los resultados que encontramos (hasta 20)
        for anuncio in anuncios:
            precio = float(anuncio['adv']['price'])
            suma += precio
            cantidad += 1
            
        return suma / cantidad if cantidad > 0 else 0.0

    except Exception as e:
        print(f"Error en {tipo_orden}: {e}")
        return 0.0

# --- FUNCIÓN PRINCIPAL QUE UNE TODO ---
def obtener_promedio_mercado():
    # 1. Obtenemos el precio de venta (A cómo comprar dólares)
    promedio_venta_usdt = consultar_binance("BUY")
    
    # 2. Obtenemos el precio de compra (A cómo vender dólares)
    promedio_compra_usdt = consultar_binance("SELL")
    
    # 3. Calculamos el promedio justo entre los dos
    if promedio_venta_usdt > 0 and promedio_compra_usdt > 0:
        promedio_final = (promedio_venta_usdt + promedio_compra_usdt) / 2
        return promedio_final
    elif promedio_venta_usdt > 0:
        return promedio_venta_usdt # Si falla uno, usamos el otro
    else:
        return 0.0 # Si fallan los dos

# --- SCRAPING BCV (IGUAL QUE ANTES) ---
def obtener_euro_bcv_directo():
    try:
        url = "https://www.bcv.org.ve"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        euro_div = soup.find('div', {'id': 'euro'})
        texto_tasa = euro_div.find('strong').text.strip()
        return float(texto_tasa.replace(',', '.'))
    except:
        return 0.0

@app.route('/tasas')
def tasas():
    # DATOS PRO (Binance Promedio + BCV)
    precio_usdt = obtener_promedio_mercado()
    precio_euro_bcv = obtener_euro_bcv_directo()
    
    # RESPALDO (DolarApi)
    try:
        oficial = requests.get("https://ve.dolarapi.com/v1/dolares/oficial").json()["promedio"]
    except:
        oficial = 0.0

    # LÓGICA DE RESPUESTA
    if precio_usdt > 0:
        usdt_final = precio_usdt
        fuente_usdt = "Binance (Promedio Compra/Venta)"
    else:
        try:
            usdt_final = requests.get("https://ve.dolarapi.com/v1/dolares/paralelo").json()["promedio"]
            fuente_usdt = "API (Respaldo)"
        except:
            usdt_final = 0.0

    if precio_euro_bcv > 0:
        euro_final = precio_euro_bcv
    else:
        try:
            factor = requests.get("https://open.er-api.com/v6/latest/EUR").json()["rates"]["USD"]
            euro_final = oficial * factor
        except:
            euro_final = 0.0

    return jsonify({
        "oficial": oficial,
        "paralelo": usdt_final,
        "euro": euro_final,
        "fuente": fuente_usdt
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
