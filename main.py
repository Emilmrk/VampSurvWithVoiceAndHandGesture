from game import iniciar_juego, controlar_juego
from gestos import reconocer_gestos
import threading
import time
import signal

stop_event = threading.Event()

def signal_handler(sig, frame):
    print("Interrupción con Ctrl+C detectada. Deteniendo el programa...")
    stop_event.set()

signal.signal(signal.SIGINT, signal_handler)

def mensaje_periodico():
    while not stop_event.is_set():
        print("Sistema escuchando...")
        time.sleep(5)

def main():
    iniciar_juego()
    print("Iniciando hilos...")  # Mensaje de depuración
    
    voz_thread = threading.Thread(target=controlar_juego, args=(stop_event,))
    gestos_thread = threading.Thread(target=reconocer_gestos, args=(stop_event,))
    mensaje_thread = threading.Thread(target=mensaje_periodico)
    
    voz_thread.start()
    gestos_thread.start()
    mensaje_thread.start()

    voz_thread.join()
    gestos_thread.join()
    mensaje_thread.join()

if __name__ == "__main__":
    main()

    main()
