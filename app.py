from flask import Flask, render_template, request, jsonify
import re
from collections import Counter
import webbrowser
from threading import Timer
from datetime import datetime

app = Flask(__name__)

def parsear_fecha(fecha_str):
    fecha_str = fecha_str.replace('-', '/').replace('.', '/')
    for fmt in ['%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d', '%d/%m']:
        try:
            dt = datetime.strptime(fecha_str.strip(), fmt)
            if dt.year < 100: dt = dt.replace(year=dt.year + 2000)
            return dt
        except ValueError:
            continue
    return None

def procesar_chat(texto_chat, fecha_inicio=None, fecha_fin=None, tipo_inmueble=None):
    patron_palabras = r"\b(requiero|solicito|necesito|compro|se requiere|se necesita|se solicita|se busca)\b"
    lineas = texto_chat.split('\n')
    requerimientos_lista = []
    inmuebles_conteo = []
    agentes_lista = []
    vistos = set()

    patron_mensaje = re.compile(r"^\[?(\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{2,4}),?\s\d{1,2}:\d{2}(?::\d{2})?\]?\s(?:-\s)?([^:]+):\s(.*)$")

    for linea in lineas:
        match = patron_mensaje.match(linea.strip())
        if match:
            fecha_str, contacto, mensaje = match.groups()
            fecha_obj = parsear_fecha(fecha_str)

            # 🗓️ Filtro por fecha
            if fecha_inicio and fecha_obj and fecha_obj < fecha_inicio: continue
            if fecha_fin and fecha_obj and fecha_obj > fecha_fin: continue

            if re.search(patron_palabras, mensaje, re.IGNORECASE):
                hash_mensaje = mensaje.strip().lower()
                if hash_mensaje not in vistos:
                    vistos.add(hash_mensaje)

                    # 🏠 Clasificación
                    msg_lower = mensaje.lower()
                    tipo_detectado = "Otro"
                    if any(p in msg_lower for p in ["casa", "quinta", "chalet", "duplex"]): tipo_detectado = "Casa"
                    elif any(p in msg_lower for p in ["apartamento", "apto", "depto", "ph", "flat"]): tipo_detectado = "Apartamento"
                    elif any(p in msg_lower for p in ["local", "oficina", "consultorio", "comercial"]): tipo_detectado = "Local/Oficina"
                    elif any(p in msg_lower for p in ["terreno", "finca", "lote", "parcela"]): tipo_detectado = "Terreno"
                    elif any(p in msg_lower for p in ["galpon", "galpón", "bodega", "almacén"]): tipo_detectado = "Galpón"

                    # 🏷️ Filtro por tipo
                    if tipo_inmueble and tipo_detectado != tipo_inmueble: continue

                    telefono_match = re.search(r"(\+?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{4,7})", mensaje)
                    telefono = telefono_match.group(1) if telefono_match else "No especificado"

                    requerimientos_lista.append({
                        "fecha": fecha_str,
                        "requerimiento": mensaje,
                        "contacto": contacto,
                        "telefono": telefono,
                        "tipo_inmueble": tipo_detectado
                    })
                    inmuebles_conteo.append(tipo_detectado)
                    agentes_lista.append(contacto)

    conteo_propiedades = dict(Counter(inmuebles_conteo))
    ranking_agentes = [{"nombre": k, "mensajes": v} for k, v in Counter(agentes_lista).most_common(5)]

    return {
        "tabla": requerimientos_lista,
        "estadisticas": conteo_propiedades,
        "ranking": ranking_agentes
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No se subió ningún archivo"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Archivo vacío"}), 400

    texto_chat = file.read().decode('utf-8', errors='ignore')

    fecha_inicio_str = request.form.get('fecha_inicio')
    fecha_fin_str = request.form.get('fecha_fin')
    tipo_inmueble = request.form.get('tipo_inmueble') or None

    f_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d') if fecha_inicio_str else None
    f_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59) if fecha_fin_str else None

    resultados = procesar_chat(texto_chat, f_inicio, f_fin, tipo_inmueble)
    
    response = jsonify(resultados)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response

def abrir_navegador():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    Timer(1.5, abrir_navegador).start()
    app.run(debug=False, port=5000)