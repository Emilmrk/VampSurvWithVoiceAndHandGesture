"""
Script de prueba para verificación rápida del micrófono y reconocimiento de voz.
Permite comprobar si el micrófono capta audio y si Google Speech API responde.
"""
import speech_recognition as sr

def probar_microfono():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    try:
        microphone = sr.Microphone()
    except Exception as e:
        print(f"[ERROR] No se pudo acceder al micrófono: {e}")
        return

    print("=" * 50)
    print("      PRUEBA DE RECONOCIMIENTO DE VOZ")
    print("=" * 50)
    print("[1/2] Calibrando ruido ambiental por 1 segundo...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
    print("Calibración completada.")

    print("\n[2/2] Di palabras como 'arriba', 'abajo', 'mover', 'hola'.")
    print("Presiona Ctrl+C para finalizar.\n")

    while True:
        try:
            with microphone as source:
                print(">> Escuchando...")
                audio = recognizer.listen(source, timeout=3.0, phrase_time_limit=4.0)

            print(">> Procesando audio...")
            texto = recognizer.recognize_google(audio, language="es-ES").lower()
            print(f"-> Has dicho: '{texto}'\n")

        except sr.WaitTimeoutError:
            print("(Silencio prolongado, reintentando...)")
        except sr.UnknownValueError:
            print("(No se entendió con claridad, intenta de nuevo)\n")
        except sr.RequestError as e:
            print(f"[ERROR DE RED] No se pudo contactar a Google API: {e}\n")
        except KeyboardInterrupt:
            print("\nPrueba finalizada por el usuario.")
            break

if __name__ == "__main__":
    probar_microfono()
