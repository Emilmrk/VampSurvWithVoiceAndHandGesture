import speech_recognition as sr
import time

recognizer = sr.Recognizer()

def reconocer_voz():
    while True:
        with sr.Microphone() as source:
            print("Di algo:")
            audio = recognizer.listen(source)

            try:
                texto = recognizer.recognize_google(audio, language="es-ES").lower()
                print("Has dicho: " + texto)  # Imprime el texto reconocido en la consola
                return texto  # Solo sale del ciclo al reconocer correctamente
            except sr.UnknownValueError:
                print("Lo siento, no pude entender lo que dijiste. Intenta de nuevo.")
                continue  # Aseguramos que siempre continúa después de manejar una excepción
            except sr.RequestError as e:
                print(f"No pude acceder al servicio de Google. Error: {e}. Verifica tu conexión.")
                continue  # Aseguramos que siempre continúa después de manejar una excepción

        print("Reintentando...")
        time.sleep(1)  # Pausa breve antes de reintentar
