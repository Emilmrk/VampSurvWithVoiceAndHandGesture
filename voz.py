"""
Módulo de reconocimiento de voz.
Soporta:
1. Vosk (Modo Offline de Alta Velocidad, latencia <50ms) si está disponible.
2. SpeechRecognition (Google Web Speech API) como respaldo universal sin congelar el hilo.
"""
import time
import speech_recognition as sr
from state import app_state

def escuchar_con_google(callback_comando):
    """
    Escucha por voz usando SpeechRecognition con timeouts para permitir
    cancelación limpia con stop_event y sin bloqueos infinitos.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    try:
        microphone = sr.Microphone()
    except Exception as e:
        print(f"[VOZ ERROR] No se detectó micrófono: {e}")
        return

    print("[VOZ] Calibrando micrófono contra ruido ambiental (1s)...")
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
    except Exception as e:
        print(f"[VOZ AVISO] No se pudo ajustar ruido ambiental: {e}")

    print("[VOZ] Listo para escuchar comandos (di 'arriba', 'abajo', 'mover', 'detener', etc.).")

    while not app_state.stop_event.is_set():
        try:
            with microphone as source:
                audio = recognizer.listen(source, timeout=1.5, phrase_time_limit=3.0)

            try:
                texto = recognizer.recognize_google(audio, language="es-ES").lower()
                continuar = callback_comando(texto)
                if not continuar:
                    break
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"[VOZ ERROR] Error de conexión con Google API: {e}")
                time.sleep(1)

        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            if not app_state.stop_event.is_set():
                print(f"[VOZ EXCEPCIÓN] {e}")
            time.sleep(0.5)

def escuchar_con_vosk(callback_comando):
    """
    Escucha por voz con Vosk (100% offline, latencia ultra-baja).
    """
    import json
    import queue
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer

    audio_queue = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        audio_queue.put(bytes(indata))

    print("[VOZ OFFLINE] Cargando modelo local Vosk...")
    model = Model(lang="es")
    rec = KaldiRecognizer(model, 16000)

    with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype='int16',
                           channels=1, callback=audio_callback):
        print("[VOZ OFFLINE] Escuchando comandos en tiempo real...")
        while not app_state.stop_event.is_set():
            try:
                data = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                texto = res.get("text", "").strip()
                if texto:
                    continuar = callback_comando(texto)
                    if not continuar:
                        break

def escuchar_comando_continuo(callback_comando):
    """
    Punto de entrada: intenta usar Vosk para cero latencia si está disponible;
    de lo contrario, recurre a Google Speech Recognition optimizado.
    """
    try:
        escuchar_con_vosk(callback_comando)
    except Exception:
        escuchar_con_google(callback_comando)
