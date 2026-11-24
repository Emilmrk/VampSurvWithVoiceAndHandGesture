"""
Script de prueba para síntesis de voz (Text-to-Speech) con pyttsx3.
Permite verificar la salida de audio por altavoces / auriculares.
"""
import threading

def speak(text):
    """Sintetiza voz de manera segura en un hilo independiente."""
    def run_speak():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            print("[TTS] Texto reproducido con éxito.")
        except Exception as e:
            print(f"[TTS ERROR] No se pudo inicializar pyttsx3: {e}")

    speak_thread = threading.Thread(target=run_speak)
    speak_thread.start()
    speak_thread.join()

if __name__ == "__main__":
    print("Probando síntesis de voz...")
    speak("Sistema de control por voz y gestos listo.")
    print("Prueba completada.")
