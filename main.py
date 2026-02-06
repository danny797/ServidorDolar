from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup # Necesaria para "leer" la página del BCV
import urllib3

# Desactivamos la advertencia de seguridad porque el certificado del BCV es malo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def obtener_euro_bcv_directo():
    try:
        # 1. Entramos a la página oficial del BCV
        # IMPORTANTE: verify=False es el secreto para que no falle por SSL
        url = "https://www.bcv.org.ve"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        
        # 2. Buscamos el div que tiene el ID "euro"
        soup = BeautifulSoup(response.content, 'html.parser')
        euro_div = soup.find('div', {'id': 'euro'})
        
        # 3. Limpiamos el texto (El BCV pone comas en vez de puntos)
        texto_tasa = euro_div.find('strong').text.strip()
        tasa_limpia = texto_tasa.replace(',', '.')
        
        return float(tasa_limpia)

    except Exception as e:
        print(f"Error raspando BCV: {e}")
        return 0.0 # Si falla, devolveremos 0 para usar el cálculo de respaldo

# --- TU FUNCIÓN DE BINANCE (LA QUE YA TIENES) ---
def obtener_precio_binance():
    # ... (Pega aquí tu código de Binance que ya funcionaba) ...
    # (Por espacio no lo repito, pero déjalo tal cual)
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        payload = {
            "asset": "USDT", "fiat": "VES", "merchantCheck": False, "page": 1,
            "publisherType": None, "rows": 10, "tradeType": "BUY", "transAmount": "500"
        }
        headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        anuncios = response.json()['data']
        suma = 0.0
        for i in range(min(5, len(anuncios))):
            suma += float(anuncios[i]['adv']['price'])
        return suma / min(5, len(anuncios))
    except:
        return 0.0

@app.route('/tasas')
def tasas():
    # 1. Intentamos las fuentes PRO (Binance + BCV Directo)
    precio_usdt = obtener_precio_binance()
    precio_euro_bcv = obtener_euro_bcv_directo()
    
    # 2. Respaldo (DolarApi) por si acaso
    try:
        oficial = requests.get("https://ve.dolarapi.com/v1/dolares/oficial").json()["promedio"]
    except:
        oficial = 0.0

    # Lógica del Euro: Si logramos raspar el BCV, usamos ese. Si no, calculamos.
    if precio_euro_bcv > 0:
        euro_final = precio_euro_bcv
        fuente_euro = "BCV Directo"
    else:
        # Cálculo matemático de respaldo
        try:
            factor = requests.get("https://open.er-api.com/v6/latest/EUR").json()["rates"]["USD"]
            euro_final = oficial * factor
            fuente_euro = "Calculado (Backup)"
        except:
            euro_final = 0.0

    # Lógica del USDT
    if precio_usdt > 0:
        usdt_final = precio_usdt
        fuente_usdt = "Binance P2P"
    else:
        # Si falla Binance, usamos el paralelo de API
        try:
            usdt_final = requests.get("https://ve.dolarapi.com/v1/dolares/paralelo").json()["promedio"]
            fuente_usdt = "API (Respaldo)"
        except:
            usdt_final = 0.0

    return jsonify({
        "oficial": oficial,
        "paralelo": usdt_final,
        "euro": euro_final,
        "fuente_usdt": fuente_usdt,
        "fuente_euro": fuente_euro
    })
