from multiprocessing import Process
import time
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from google import genai

import os
from dotenv import load_dotenv


load_dotenv()

apiGoogle=os.getenv("apiGoogle")
#Paso1. configurar gemini
cliente=genai.Client(api_key=apiGoogle)
modelo="gemini-3.5-flash-lite"

optimizacionGemini=asyncio.Semaphore(3)

#Paso2. Configurar las funcion de informacion de conocimiento
def cargarInformacion():
    try: 
        with open("chat/informacion.txt","r",encoding="utf-8") as archivo:
            return archivo.read()
    except FileNotFoundError:
        return ""

contexto=cargarInformacion() #Contexto cargado una sola vez

async def responder(update:Update,context:ContextTypes.DEFAULT_TYPE):
    pregunta=update.message.text
    #contexto=cargarInformacion()
    if not contexto.strip():
        await update.message.reply_text("Error al activar la base de conocimiento...")
        return
    #mensajeEspera=await update.message.reply_text("Analizando...")
    pregunta=pregunta[:1000]
    try:
        indicacion=f"""
            Debes responder de forma cordial las consultas de los usuarios
            Solo debes utilizar como fuente principal el siguiente archivo: 
            {contexto}

            Reglas:
            1. Responde solo basandote en el material proporcianado
            2. Si no tienes informacion suficiente puedes buscarlo en tu base de datos
            pero sin salir del tema especifico para tu busqueda
            3. Usa mensajes cortos, respondiendo los mas humano posible como un asistente de atencion al cliente
            4. recepciona y solicita datos para registro de los interesados puedes ser persuasvio
            5. No utilizar ** para el uso de negrita, usar un texto plano
            6. Agrega empojis en tus respuestas. solo uno o dos por mensaje
            7. si el usuario te proporciono su nombre, fecha, habitacion o cantidad de personas, conserva esos datos durante la conversacion 

            Pregunta del usuario: {pregunta}
        """
        async with optimizacionGemini:      
            respuesta=await asyncio.to_thread(
                cliente.models.generate_content,
                    model=modelo,
                    contents=indicacion
            )
            texto=respuesta.text or ("Error al procesar")
            for inicio in range(0,len(texto),2000):
                await update.message.reply_text(texto[inicio:inicio+2000])
    except Exception as error:
        print("Error al conectar",error)

async def imagenEnviar(update:Update,context:ContextTypes.DEFAULT_TYPE):
    with open("chat/telegram.jpg","rb") as imagen:
        await update.message.reply_photo(photo=imagen)

async def pdfEnviar(update:Update,context:ContextTypes.DEFAULT_TYPE):
    with open("chat/practica.pdf","rb") as pdf:
        await update.message.reply_document(pdf)

async def audioEnviar(update:Update,context:ContextTypes.DEFAULT_TYPE):
    with open("chat/musica.mp3","rb") as musica:
        await update.message.reply_audio(musica)

def simulacion():
    print("Proceso iniciado...")

    for i in range(1, 11):
        print(f"Proceso {i} iniciado")
        time.sleep(1)

    print("Proceso finalizado")




async def procesar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Crear un nuevo proceso
    proceso = Process(target=simulacion)

    # Iniciar el proceso
    proceso.start()

   
    await update.message.reply_text(
        f"✅ Proceso iniciado correctamente.\n"
        f"PID del proceso: {proceso.pid}"
    )




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Hola, bienvenido al bot.\n\n"
        "Comandos disponibles:\n"
        "/procesar - Iniciar un proceso\n"
        "/reservas - Consultar reservas\n"
    )




async def reservas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🛒 RESERVAS\n\n"
        "1. nombre\n"
        "2. pieza\n"
        "3. fecha de llegada\n"
        "4. para cuantas personas"
    )




if __name__ == "__main__":

    
    TOKEN =os.getenv("tokenTelegram")

    
    app = ApplicationBuilder().token(TOKEN).build()

   
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("procesar", procesar))
    app.add_handler(CommandHandler("reservas", reservas))
    app.add_handler(CommandHandler("imagen",imagenEnviar))
    app.add_handler(CommandHandler("practica",pdfEnviar))
    app.add_handler(CommandHandler("musica",audioEnviar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,responder))

    print(" Bot iniciado...")
    print("Esperando comandos...")

    # Ejecutar bot
    app.run_polling()