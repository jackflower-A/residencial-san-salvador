
# PASO 1. IMPORTAR LAS DEPENDENCIAS
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import requests
import os
import time
from dotenv import load_dotenv
from google import genai
from pathlib import Path
from flask import request

# Historial independiente para cada conexion
historiales = {}

# PASO 2. CARGAR LAS VARIABLES DE ENTORNO
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
# CONFIGURAR GEMINI
BASE_DIR = Path(__file__).resolve().parent

apiGoogle = os.getenv("apiGoogle")

cliente = genai.Client(api_key=apiGoogle) if apiGoogle else None

modelo = "gemini-3.5-flash-lite"

# CARGAR INFORMACION
ruta = BASE_DIR / "informacion.txt"

if ruta.exists():
    informacion = ruta.read_text(encoding="utf-8")
else:
    informacion = ""

token = os.getenv("tokenTelegram")
chat_id = os.getenv("chatIdTelegram")

# PASO 3. CONFIGURAR FLASK Y SOCKETIO
app = Flask(__name__)
socket = SocketIO(app, cors_allowed_origins="*")

# URL DE TELEGRAM
url_enviar = f"https://api.telegram.org/bot{token}/sendMessage"
url_recibir = f"https://api.telegram.org/bot{token}/getUpdates"



# PASO 4. RUTA PRINCIPAL
@app.route("/")
def inicio():
    return render_template(
        "login.html",
        apiKey=os.getenv("apiKey"),
        authDomain=os.getenv("authDomain"),
        projectId=os.getenv("projectId"),
        storageBucket=os.getenv("storageBucket"),
        messagingSenderId=os.getenv("messagingSenderId"),
        appId=os.getenv("appId"),
        measurementId=os.getenv("measurementId")
    )


# PASO 5. RUTA DEL CHAT
@app.route("/chat")
def chat():
    return render_template(
        "index.html",
        apiKey=os.getenv("apiKey"),
        authDomain=os.getenv("authDomain"),
        projectId=os.getenv("projectId"),
        storageBucket=os.getenv("storageBucket"),
        messagingSenderId=os.getenv("messagingSenderId"),
        appId=os.getenv("appId"),
        measurementId=os.getenv("measurementId")
    )


# PASO 6. ENVIAR MENSAJES A TELEGRAM
def enviarTelegram(texto):
    try:
        respuesta = requests.post(
            url_enviar,
            data={
                "chat_id": chat_id,
                "text": texto
            },
            timeout=10
        )

        datos = respuesta.json()

        if datos.get("ok"):
            print("Mensaje enviado a Telegram")
        else:
            print("Error de Telegram:", datos)

    except requests.RequestException as error:
        print("Error al enviar a Telegram:", error)

palabras_especificas={
    "ayuda":"Alerta: Usuario solicita ayuda",
    "soporte":"Alerta: Usuario solicita apoyo",
    "imagen":"Imagen solicitada",
    "reporte": "Reporte solicitado",

}

# PASO 7. RECIBIR MENSAJES DEL CHAT WEB


# PASO 7. RECIBIR MENSAJES Y RESPONDER CON GEMINI

@socket.on("message")
def recibir_mensaje(mensaje):

    texto = str(mensaje).strip()

    if not texto:
        return

    print("Usuario:", texto)

    # Mostrar el mensaje solamente al usuario que lo envio
    emit("mensaje", texto)

    # Comprobar si Gemini esta configurado
    if cliente is None:
        emit("respuesta_gemini", {
            "texto": "ERROR: No se encontro apiGoogle en .env"
        })
        return

    try:
        indicacion = f"""
        Eres el asistente virtual del Residencial San Salvador.

        INFORMACION:
        {informacion}

        REGLAS IMPORTANTES:

        1. Habla de manera natural, amable y profesional.

        2. No repitas preguntas que ya fueron respondidas.

        3. Recuerda los datos proporcionados por el cliente
        durante la conversacion.

        4. Solicita solamente los datos que falten.

        5. Haz una o dos preguntas por respuesta.

        6. Si el usuario dice "gracias", responde brevemente
        y no vuelvas a solicitar los datos de reserva.

        7. No repitas listas completas de requisitos
        en cada mensaje.

        8. Si el cliente ya proporciono su nombre, fecha,
        habitacion o cantidad de personas, conserva
        esos datos durante la conversacion.

        9. Cuando tengas todos los datos, presenta un
        resumen de la solicitud y explica que recepcion
        verificara la disponibilidad.

        10. No inventes precios ni confirmes reservas
        sin verificar la disponibilidad.

        11. solo saluda al usuario si es la primera vez que interactua contigo.

        Ayuda a los clientes con reservas de habitaciones.
        Responde en español de forma amable y breve.
        Solicita los datos necesarios para una reserva.
        No inventes precios ni confirmes disponibilidad.

        Mensaje del cliente:
        {texto}
        """

        respuesta = cliente.models.generate_content(
            model="gemini-3.5-flash-lite",
            
            contents=indicacion
        )

        texto_respuesta = respuesta.text or "Sin respuesta de Gemini"

        print("Gemini:", texto_respuesta)

        emit("respuesta_gemini", {
            "texto": texto_respuesta
        })

    except Exception as error:

        print("ERROR GEMINI:", repr(error))

        emit("respuesta_gemini", {
            "texto": "Error de Gemini: " + str(error)[:300]
        })

# PASO 8. RECIBIR MENSAJES DESDE TELEGRAM
def recibirTelegram():

    ultimo_id = 0

    while True:
        try:
            respuesta = requests.get(
                url_recibir,
                params={
                    "offset": ultimo_id + 1,
                    "timeout": 10
                },
                timeout=20
            )

            datos = respuesta.json()

            if not datos.get("ok"):
                print("Error al consultar Telegram:", datos)
                time.sleep(2)
                continue

            for actualizacion in datos.get("result", []):

                ultimo_id = actualizacion["update_id"]

                if "message" in actualizacion:
                    mensaje = actualizacion["message"]
                    texto = mensaje.get("text", "")

                    # IGNORAR MENSAJES SIN TEXTO
                    if texto:
                        print("Telegram:", texto)

                        # ENVIAR EL MENSAJE AL CHAT WEB
                        socket.emit(
                            "mensaje_telegram",
                            {"texto": texto}
                        )

        except (requests.RequestException, ValueError) as error:
            print("Error al recibir de Telegram:", error)
            time.sleep(2)


# PASO 9. INICIAR EL SERVIDOR
if __name__ == "__main__":

    hilo = threading.Thread(
        target=recibirTelegram,
        daemon=True
    )
    hilo.start()

    socket.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT",5000)),
        debug=True,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )