"""
Signos del zodiaco - app de recolección de dibujos.

Basado en la app de letras de clase (U, N, I): una página con un lienzo donde
se dibuja el signo pedido y cada dibujo se guarda como PNG en la carpeta de
su clase. Esos PNG son los datos con los que se entrena la red neuronal.
"""
import base64
import binascii
import io
import os
import random
import re
import time
import uuid
import zipfile

import numpy as np
from flask import Flask, abort, jsonify, render_template, request, send_file
from PIL import Image

app = Flask(__name__)

# Signos del zodiaco: carpeta -> datos que se muestran
SIGNOS = {
    "aries":   {"nombre": "Aries",   "elemento": "fuego",  "fechas": "21 mar - 19 abr"},
    "tauro":   {"nombre": "Tauro",   "elemento": "tierra", "fechas": "20 abr - 20 may"},
    "geminis": {"nombre": "Géminis", "elemento": "aire",   "fechas": "21 may - 20 jun"},
    "cancer":  {"nombre": "Cáncer",  "elemento": "agua",   "fechas": "21 jun - 22 jul"},
    "leo":     {"nombre": "Leo",     "elemento": "fuego",  "fechas": "23 jul - 22 ago"},
    "acuario": {"nombre": "Acuario", "elemento": "aire",   "fechas": "20 ene - 18 feb"},
}
CLASES = {clave: s["nombre"] for clave, s in SIGNOS.items()}
META_POR_CLASE = 800   # minimo  por la práctica
LADO = 200             # lienzo de 200x200 px 

DATA_DIR = (
    os.environ.get("DATA_DIR")
    or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
)

# Minimo de píxeles pintados para aceptar un dibujo 
MIN_PIXELES_PINTADOS = 150


def crear_carpetas():
    for clase in CLASES:
        os.makedirs(os.path.join(DATA_DIR, clase), exist_ok=True)


def archivos_de(clase):
    carpeta = os.path.join(DATA_DIR, clase)
    if not os.path.isdir(carpeta):
        return []
    return sorted(f for f in os.listdir(carpeta) if f.endswith(".png"))


def conteo():
    return {clase: len(archivos_de(clase)) for clase in CLASES}


def elegir_siguiente(evitar=None):
    """Elige el próximo signo a dibujar.

    Las clases con menos dibujos tienen más probabilidad de salir, así el
    conjunto de datos queda balanceado aunque cada persona dibuje distinto
    número de veces.
    """
    c = conteo()
    opciones = [k for k in CLASES if k != evitar] or list(CLASES)
    maximo = max(c.values())
    pesos = [(maximo - c[k] + 1) ** 2 for k in opciones]
    return random.choices(opciones, weights=pesos, k=1)[0]


def limpiar_autor(texto):
    texto = (texto or "").strip().lower()
    texto = (texto.replace("á", "a").replace("é", "e").replace("í", "i")
                  .replace("ó", "o").replace("ú", "u").replace("ñ", "n"))
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto[:20] or "anonimo"


def decodificar_png(data_url):
    """Convierte el dataURL del lienzo en una imagen RGBA de 200x200."""
    if not data_url or not data_url.startswith("data:image/png;base64,"):
        return None
    try:
        crudo = base64.b64decode(data_url.split(",", 1)[1], validate=True)
        img = Image.open(io.BytesIO(crudo))
        img.load()
    except (binascii.Error, ValueError, OSError):
        return None
    if img.size != (LADO, LADO):
        return None
    return img.convert("RGBA")


# ---------------------------------------------------------------- páginas

def leer_referencias():
    """Lee los SVG de referencia para mostrarlos dentro de la página."""
    carpeta = os.path.join(app.static_folder, "referencias")
    refs = {}
    for clase in CLASES:
        with open(os.path.join(carpeta, f"{clase}.svg"), encoding="utf-8") as f:
            refs[clase] = f.read()
    return refs


REFERENCIAS = leer_referencias()


@app.route("/")
def inicio():
    return render_template(
        "index.html",
        clases=CLASES,
        signos=SIGNOS,
        referencias=REFERENCIAS,
        meta=META_POR_CLASE,
        lado=LADO,
    )


# ---------------------------------------------------------------- API

@app.route("/api/estado")
def estado():
    return jsonify(conteo=conteo(), meta=META_POR_CLASE,
                   siguiente=elegir_siguiente(request.args.get("evitar")))


@app.route("/api/guardar", methods=["POST"])
def guardar():
    datos = request.get_json(silent=True) or {}
    clase = datos.get("clase")
    if clase not in CLASES:
        return jsonify(error="Signo desconocido."), 400

    img = decodificar_png(datos.get("imagen"))
    if img is None:
        return jsonify(error="La imagen no es válida."), 400

    # el trazo queda en el canal alfa
    alfa = np.asarray(img)[:, :, 3]
    if int((alfa > 0).sum()) < MIN_PIXELES_PINTADOS:
        return jsonify(error="El dibujo está casi vacío. Dibuja el signo completo."), 400

    autor = limpiar_autor(datos.get("autor"))
    nombre = f"{autor}_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
    crear_carpetas()
    img.save(os.path.join(DATA_DIR, clase, nombre))

    return jsonify(ok=True, clase=clase, archivo=nombre, conteo=conteo(),
                   siguiente=elegir_siguiente(evitar=clase))


@app.route("/api/deshacer", methods=["POST"])
def deshacer():
    """Borra un dibujo recién enviado (por si se envió uno mal hecho)."""
    datos = request.get_json(silent=True) or {}
    clase = datos.get("clase")
    archivo = datos.get("archivo", "")
    if clase not in CLASES or not re.fullmatch(r"[a-z0-9-]+_\d+_[0-9a-f]{8}\.png", archivo):
        return jsonify(error="No se encontró ese dibujo."), 400
    ruta = os.path.join(DATA_DIR, clase, archivo)
    if not os.path.isfile(ruta):
        return jsonify(error="Ese dibujo ya no existe."), 404
    os.remove(ruta)
    return jsonify(ok=True, conteo=conteo())


# ---------------------------------------------------------------- descargas

@app.route("/descargar")
def descargar_zip():
    """Todos los dibujos en un .zip, con una carpeta por clase."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for clase in CLASES:
            for f in archivos_de(clase):
                z.write(os.path.join(DATA_DIR, clase, f), arcname=f"{clase}/{f}")
    buffer.seek(0)
    return send_file(buffer, mimetype="application/zip", as_attachment=True,
                     download_name="zodiaco_dibujos.zip")


@app.route("/prepare")
def preparar_dataset():
    """Arma X.npy (n, 200, 200) e y.npy (n,) como en la app original."""
    imagenes, etiquetas = [], []
    for clase in CLASES:
        for f in archivos_de(clase):
            img = Image.open(os.path.join(DATA_DIR, clase, f)).convert("RGBA")
            imagenes.append(np.asarray(img)[:, :, 3])
            etiquetas.append(clase)
    if not imagenes:
        return "Todavía no hay dibujos.", 400
    np.save(os.path.join(DATA_DIR, "X.npy"), np.stack(imagenes))
    np.save(os.path.join(DATA_DIR, "y.npy"), np.array(etiquetas))
    return f"OK! {len(imagenes)} dibujos. Descarga /X.npy y /y.npy"


@app.route("/X.npy")
def descargar_x():
    return enviar_npy("X.npy")


@app.route("/y.npy")
def descargar_y():
    return enviar_npy("y.npy")


def enviar_npy(nombre):
    ruta = os.path.join(DATA_DIR, nombre)
    if not os.path.isfile(ruta):
        abort(404, "Primero entra a /prepare")
    return send_file(ruta, as_attachment=True)


crear_carpetas()

if __name__ == "__main__":
    app.run(debug=True)
