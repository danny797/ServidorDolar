from flask import Flask, jsonify
import requests

app = Flask(__name__)

# --- FUNCIÓN PARA CONSULTAR BINANCE P2P DIRECTAMENTE ---
def obtener_precio_binance():
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        
        # Le decimos a Binance que queremos COMPRAR (BUY) USDT pagando con VES (Bolívares)
        # Filtramos por "Pago Móvil" (transferencia bancaria) que es lo más común
        payload = {
            "asset": "USDT",
            "fiat": "VES",
            "merchantCheck": False,
            "page": 1,
            "publisherType": None,
            "rows": 10,
            "tradeType": "BUY",
            "transAmount": "500" # Simulamos comprar 500 Bs para ver precios reales
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        data = response.json()
        
        # Obtenemos los anuncios de la respuesta
        anuncios = data['data']
        
        # Calculamos el promedio de los primeros 5 precios para evitar estafas o precios falsos
        suma = 0.0
        cantidad = 0
        for i in range(min(5, len(anuncios))):
            precio = float(anuncios[i]['adv']['price'])
            suma += precio
            cantidad += 1
            
        promedio = suma / cantidad
        return promedio

    except Exception as e:
        print(f"Error Binance: {e}")
        return None

# --- FUNCIÓN DE RESPALDO (DOLARAPI) ---
def obtener_respaldo():
    try:
        oficial = requests.get("https://ve.dolarapi.com/v1/dolares/oficial").json()["promedio"]
        paralelo = requests.get("https://ve.dolarapi.com/v1/dolares/paralelo").json()["promedio"]
        return oficial, paralelo
    except:
        return 0.0, 0.0

@app.route('/tasas')
def tasas():
    # 1. Intentamos obtener el precio REAL de Binance
    precio_usdt = obtener_precio_binance()
    
    # 2. Obtenemos el oficial y respaldo por si acaso
    oficial, paralelo_backup = obtener_respaldo()
    
    # Si Binance falló (nos bloquearon), usamos el paralelo de respaldo
    if precio_usdt is None or precio_usdt == 0:
        precio_usdt = paralelo_backup
        fuente_usdt = "DolarApi (Respaldo)"
    else:
        fuente_usdt = "Binance P2P (En vivo)"

    # 3. Calculamos Euro (Matemático)
    try:
        euro_mundial = requests.get("https://open.er-api.com/v6/latest/EUR").json()["rates"]["USD"]
        precio_euro = oficial * euro_mundial
    except:
        precio_euro = 0.0

    return jsonify({
        "oficial": oficial,
        "paralelo": precio_usdt, # Aquí mandamos el de Binance real
        "euro": precio_euro,
        "fuente": fuente_usdt
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
