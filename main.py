"""
Punto de entrada principal para el control de Vampire Survivors / PC con gestos y voz.
"""
import argparse
import threading
import signal

from state import app_state
from gestos import reconocer_gestos
from launcher import verificar_o_configurar_juego
from game import controlar_juego_loop, set_mouse_up, release_all_keys


def signal_handler(sig, frame):
    """Manejo de interrupción con Ctrl+C."""
    print("\n[SISTEMA] Ctrl+C detectado. Deteniendo todos los servicios...")
    app_state.stop_event.set()


def banner_inicio():
    print("=" * 68)
    print("     CONTROL HÍBRIDO (GESTOS + VOZ) - VAMPIRE SURVIVORS & PC     ")
    print("=" * 68)
    print(" [FORMAS DE SALIR SIN VOZ]")
    print("   * Presiona 'q' sobre la ventana de la cámara.")
    print("   * Cierra la ventana de la cámara con la [X].")
    print("   * Presiona Ctrl+C en esta consola.")
    print("\n [GESTOS Y ATAJOS EN VENTANA]")
    print("   * Tecla 'm': Alterna entre Modo MOUSE y Modo JOYSTICK (WASD / Flechas).")
    print("   * Tecla 'd': Activa/desactiva Modo Arrastre manual.")
    print("   * Mover índice (Modo Mouse): Desplaza el cursor.")
    print("   * Pellizco Pulgar + Índice: Clic izquierdo / Arrastrar (Espacio en Joystick).")
    print("   * Pellizco Pulgar + Medio: Clic derecho.")
    print("   * Palma Abierta (5 dedos): Parada de seguridad (suelta clics y teclas).")
    print("\n [COMANDOS DE VOZ]")
    print("   * 'abrir juego' / 'cerrar juego'")
    print("   * 'modo raton' / 'modo teclado' / 'modo flechas'")
    print("   * 'arriba' / 'abajo' / 'izquierda' / 'derecha'")
    print("   * 'mover' (arrastre continuo) / 'detener'")
    print("   * 'clic' / 'doble clic' / 'espacio' / 'enter' / 'escape' / 'captura'")
    print("   * 'salir del programa'")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(description="Control por gestos y voz")
    parser.add_argument(
        "--config",
        action="store_true",
        help="Abre el menú para elegir o cambiar la ruta del juego al iniciar"
    )
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)

    if not verificar_o_configurar_juego(forzar_menu=args.config):
        print("[SISTEMA] Inicio cancelado.")
        return

    banner_inicio()

    voz_thread = threading.Thread(target=controlar_juego_loop, name="HiloVoz", daemon=True)
    gestos_thread = threading.Thread(target=reconocer_gestos, name="HiloGestos")

    print("[SISTEMA] Iniciando hilos de procesamiento...")
    voz_thread.start()
    gestos_thread.start()

    try:
        # Polling corto para que Ctrl+C responda inmediatamente incluso en Windows
        while gestos_thread.is_alive() and not app_state.stop_event.is_set():
            gestos_thread.join(timeout=0.3)
    except KeyboardInterrupt:
        print("\n[SISTEMA] Interrupción por teclado (Ctrl+C).")
    finally:
        app_state.stop_event.set()
        set_mouse_up()
        release_all_keys()
        print("[SISTEMA] Finalizando hilo de voz...")
        voz_thread.join(timeout=2.0)
        print("[SISTEMA] Programa terminado correctamente.")


if __name__ == "__main__":
    main()
