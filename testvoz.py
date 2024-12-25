import speech_recognition as sr

recognizer = sr.Recognizer()

def reconocer_voz():
    with sr.Microphone() as source:
        print("Di algo:")
        audio = recognizer.listen(source)

        try:
            texto = recognizer.recognize_google(audio, language="es-ES").lower()
            print("Has dicho: " + texto)
            return texto
        except sr.UnknownValueError:
            print("Lo siento, no pude entender lo que dijiste. Intenta de nuevo.")
            return None
        except sr.RequestError as e:
            print(f"No pude acceder al servicio de Google. Error: {e}. Verifica tu conexión.")
            return None

if __name__ == "__main__":
    while True:
        reconocer_voz()

