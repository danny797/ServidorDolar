from flask import Flask, jsonify
import requests

app = Flask(__name__)

def obtener_de_dolartoday():
    # Identificación falsa para parecer un Chrome normal y no un robot
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://google.com'
    }
    url = "https://s3.amazonaws.com/dolartoday/data.json"
    
    response = requests.get(url, headers=headers, timeout=5)
    data = response.json()
    
    return {
        "oficial": data["USD"]["sicad2"],
        "paralelo": data["USD"]["transferencia"],
        "euro": data["EUR"]["transferencia"],
        "fuente": "DolarToday"
    }

def obtener_de_dolarapi():
    # Plan B: Si DolarToday falla, usamos DolarApi
    # Usamos el paralelo como referencia para USDT
    oficial = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5).json()
    paralelo = requests.get("https://ve.dolarapi.com/v1/dolares/paralelo", timeout=5).json()
    
    # Calculamos Euro
    euro_mundial = requests.get("https://open.er-api.com/v6/latest/EUR", timeout=5).json()
    tasa_euro = oficial["promedio"] * euro_mundial["rates"]["USD"]
    
    return {
        "oficial": oficial["promedio"],
        "paralelo": paralelo["promedio"],
        "euro": tasa_euro,
        "fuente": "DolarApi (Backup)"
    }

@app.route('/')
def home():
    return "Servidor Activo 🟢"

@app.route('/tasas')
def tasas():
    try:
        # Intento 1: DolarToday
        return jsonify(obtener_de_dolartoday())
    except Exception as e1:
        print(f"Fallo DolarToday: {e1}")
        try:
            # Intento 2: DolarApi (Plan B)
            return jsonify(obtener_de_dolarapi())
        except Exception as e2:
            return jsonify({"error": "Todas las fuentes fallaron", "detalle": str(e2)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
