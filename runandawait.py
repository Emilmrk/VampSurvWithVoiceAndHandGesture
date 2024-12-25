import pyttsx3
import threading

engine = pyttsx3.init()

def speak(text):
    def run_speak():
        engine.say(text)
        engine.startLoop(False)  # Iniciar el bucle sin bloquear
        engine.iterate()  # Procesar la cola de comandos
        engine.endLoop()  # Finalizar el bucle
        print("El texto ha sido hablado con éxito.")  # Añadimos un print para depuración

    speak_thread = threading.Thread(target=run_speak)
    speak_thread.start()
    speak_thread.join()  # Esperar a que el hilo termine

# Probar la función con un texto sencillo
speak("Esta es una prueba de síntesis de voz.")
print("Programa terminado con éxito.")
