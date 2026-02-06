from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "El servidor de Danny está vivo! Usa /tasas para ver los precios."

@app.route('/tasas')
def obtener_tasas():
    try:
        # 1. Buscamos el archivo JSON seguro de Amazon (DolarToday)
        # Usamos headers para parecer un navegador real y evitar bloqueos
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://s3.amazonaws.com/dolartoday/data.json"
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # 2. Extraemos solo lo que necesita tu App Android
        resultado = {
            "oficial": data["USD"]["sicad2"],        # Tasa BCV
            "paralelo": data["USD"]["transferencia"], # Tasa Calle/USDT
            "euro": data["EUR"]["transferencia"]      # Tasa Euro
        }
        
        return jsonify(resultado)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Esto permite correrlo en tu PC para probar si quisieras
    app.run(debug=True, host='0.0.0.0', port=5000)