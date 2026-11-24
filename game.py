"""
Módulo de control del juego y ejecución de comandos.
Soporta PyDirectInput en Windows (DirectX) y PyAutoGUI con tolerancia multiplataforma (Linux / macOS / Windows).
"""
import subprocess
import psutil
import datetime
import json
import os
import sys
import threading
import time

from state import app_state
import config

# Configuración de simulación de periféricos
USE_DIRECT_INPUT = False

if sys.platform.startswith("win") and getattr(config, "PREFER_PYDIRECTINPUT", True):
    try:
        import pydirectinput
        input_engine = pydirectinput
        input_engine.PAUSE = 0
        USE_DIRECT_INPUT = True
    except Exception:
        import pyautogui
        input_engine = pyautogui
        input_engine.PAUSE = 0
        input_engine.FAILSAFE = False
else:
    # Linux / macOS o respaldo en Windows
    try:
        if sys.platform.startswith("linux"):
            xauth_path = os.path.expanduser("~/.Xauthority")
            if not os.path.exists(xauth_path):
                try:
                    open(xauth_path, "a").close()
                except Exception:
                    pass
        import pyautogui
        input_engine = pyautogui
        input_engine.PAUSE = 0
        input_engine.FAILSAFE = False
    except Exception as e:
        print(f"[INPUT ADVERTENCIA] No se pudo inicializar PyAutoGUI: {e}")
        input_engine = None


def cargar_config_usuario():
    """Carga la ruta del juego y preferencias guardadas en user_config.json si existe."""
    if os.path.exists(config.USER_CONFIG_FILE):
        try:
            with open(config.USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("game_path"):
                app_state.game_path = data["game_path"]
            if data.get("control_mode") in ("mouse", "wasd", "arrows"):
                app_state.control_mode = data["control_mode"]
        except Exception as e:
            print(f"[CONFIG] No se pudo leer {config.USER_CONFIG_FILE}: {e}")


def guardar_config_usuario():
    """Guarda la ruta del juego y preferencias actuales en user_config.json."""
    try:
        with open(config.USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "game_path": app_state.game_path,
                "control_mode": app_state.control_mode
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[CONFIG] No se pudo guardar {config.USER_CONFIG_FILE}: {e}")


def buscar_rutas_steam_comunes():
    """Busca Vampire Survivors en rutas típicas de Steam en Windows."""
    letras = ["C", "D", "E", "F", "G"]
    subrutas = [
        r"juegos\steamapps\common\Vampire Survivors\VampireSurvivors.exe",
        r"Games\steamapps\common\Vampire Survivors\VampireSurvivors.exe",
        r"Program Files (x86)\Steam\steamapps\common\Vampire Survivors\VampireSurvivors.exe",
        r"SteamLibrary\steamapps\common\Vampire Survivors\VampireSurvivors.exe",
        r"Steam\steamapps\common\Vampire Survivors\VampireSurvivors.exe",
    ]
    for letra in letras:
        for sub in subrutas:
            candidato = f"{letra}:\\{sub}"
            if os.path.exists(candidato):
                return candidato
    return None


def _seleccionar_archivo_grafico():
    """Abre un selector de archivos nativo con tkinter si hay interfaz gráfica."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        ruta = filedialog.askopenfilename(
            title="Selecciona el ejecutable del juego",
            filetypes=[("Ejecutables", "*.exe"), ("Todos los archivos", "*.*")]
        )
        root.destroy()
        return ruta
    except Exception:
        return None


def verificar_o_configurar_juego(forzar_menu=False) -> bool:
    """
    Verifica si el juego existe en la ruta configurada.
    Si no existe (o si se fuerza el menú), permite añadir la ruta, abrir otro juego,
    continuar sin abrir juego o cancelar el programa.
    Retorna True para continuar ejecutando el sistema, False para cancelar y salir.
    """
    cargar_config_usuario()
    ruta_actual = app_state.game_path

    # Auto-detección rápida en Windows si la ruta por defecto no existe
    if not os.path.exists(ruta_actual) and not forzar_menu:
        encontrado = buscar_rutas_steam_comunes()
        if encontrado:
            print(f"[JUEGO] Auto-detectado en: {encontrado}")
            app_state.game_path = encontrado
            guardar_config_usuario()
            return True

    if os.path.exists(ruta_actual) and not forzar_menu:
        print(f"[JUEGO] Ruta verificada correctamente: {ruta_actual}")
        return True

    while True:
        print("\n" + "-" * 65)
        if not os.path.exists(app_state.game_path):
            print(f"[AVISO] No se encontró el juego en:\n  -> {app_state.game_path}")
        else:
            print(f"[CONFIGURACIÓN DE JUEGO] Ruta actual:\n  -> {app_state.game_path}")

        print("\n¿Qué deseas hacer?")
        print("  1. Ingresar manualmente la ruta del juego (.exe o ejecutable)")
        print("  2. Seleccionar otro juego con el explorador de archivos")
        print("  3. Continuar sin abrir ningún juego (controlar PC / juego ya abierto)")
        print("  4. Cancelar y salir del programa")

        try:
            opcion = input("\nElige una opción (1-4) [3]: ").strip() or "3"
        except (EOFError, KeyboardInterrupt):
            return False

        if opcion == "1":
            try:
                nueva_ruta = input("Pega la ruta completa del juego (o deja vacío para volver): ").strip().strip('"').strip("'")
            except (EOFError, KeyboardInterrupt):
                return False
            if not nueva_ruta:
                continue
            if os.path.exists(nueva_ruta):
                app_state.game_path = nueva_ruta
                guardar_config_usuario()
                print(f"[JUEGO] Ruta guardada: {nueva_ruta}")
                return True
            else:
                print(f"[ERROR] El archivo no existe en: {nueva_ruta}")

        elif opcion == "2":
            ruta_gui = _seleccionar_archivo_grafico()
            if ruta_gui and os.path.exists(ruta_gui):
                app_state.game_path = ruta_gui
                guardar_config_usuario()
                print(f"[JUEGO] Juego seleccionado y guardado: {ruta_gui}")
                return True
            else:
                print("[AVISO] No se seleccionó ningún archivo o no hay entorno gráfico para el selector.")

        elif opcion == "3":
            print("[SISTEMA] Continuando en modo libre (sin lanzar ejecutable automático).")
            return True

        elif opcion == "4":
            print("[SISTEMA] Cancelado por el usuario.")
            return False

        else:
            print("Opción no válida. Elige entre 1 y 4.")


def is_process_running(process_name=None):
    """Comprueba si el proceso del juego está en ejecución."""
    objetivo = process_name or app_state.process_name
    if not objetivo:
        return False
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == objetivo.lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def open_game():
    """Lanza el ejecutable configurado si existe y no está corriendo."""
    ruta = app_state.game_path
    proceso = app_state.process_name
    if not ruta or not os.path.exists(ruta):
        print(f"[JUEGO] No hay un ejecutable válido configurado ({ruta}).")
        print("[JUEGO] Inicia con 'python main.py --config' para añadir o elegir otro juego.")
        return

    if not is_process_running(proceso):
        try:
            subprocess.Popen(ruta, cwd=os.path.dirname(ruta) or None)
            print(f"[JUEGO] Abriendo: {ruta}")
        except Exception as e:
            print(f"[JUEGO ERROR] No se pudo abrir {ruta}: {e}")
    else:
        print(f"[JUEGO] '{proceso}' ya está en ejecución.")


def close_game():
    """Cierra el juego configurado de forma segura."""
    proceso = app_state.process_name
    if not proceso:
        print("[JUEGO] No hay proceso configurado para cerrar.")
        return

    encontrado = False
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == proceso.lower():
                proc.terminate()
                print(f"[JUEGO] Cerrando {proceso}...")
                encontrado = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not encontrado:
        print(f"[JUEGO] '{proceso}' no está en ejecución.")


def take_screenshot():
    """Toma una captura de pantalla con timestamp."""
    if input_engine is None:
        return
    os.makedirs("assets", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join("assets", f"screenshot_{timestamp}.png")
    try:
        import pyautogui
        pyautogui.screenshot(screenshot_path)
        print(f"[CAPTURA] Guardada como: {screenshot_path}")
    except Exception as e:
        print(f"[CAPTURA ERROR] No se pudo tomar captura: {e}")


def press_key(key_name: str):
    """Presiona y suelta una tecla rápidamente."""
    if input_engine is None:
        return
    try:
        input_engine.press(key_name)
    except Exception as e:
        print(f"[INPUT ERROR] Error presionando tecla {key_name}: {e}")


def hold_key_duration(key_name: str, duration: float = config.VOICE_KEY_HOLD_SECONDS):
    """Mantiene presionada una tecla durante 'duration' segundos sin bloquear el hilo actual."""
    if input_engine is None:
        return

    def _worker():
        try:
            input_engine.keyDown(key_name)
            time.sleep(duration)
        except Exception as e:
            print(f"[INPUT ERROR] Error manteniendo tecla {key_name}: {e}")
        finally:
            try:
                input_engine.keyUp(key_name)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()


def actualizar_teclas_direccion(nuevas_teclas: set):
    """
    Sincroniza las teclas mantenidas (para modo Joystick Virtual WASD/Flechas),
    soltando las que ya no están activas y presionando las nuevas.
    """
    if input_engine is None:
        return
    actuales = app_state.get_held_keys()
    if actuales == nuevas_teclas:
        return

    for k in actuales - nuevas_teclas:
        try:
            input_engine.keyUp(k)
        except Exception:
            pass

    for k in nuevas_teclas - actuales:
        try:
            input_engine.keyDown(k)
        except Exception:
            pass

    app_state.set_held_keys(nuevas_teclas)


def release_all_keys():
    """Libera todas las teclas direccionales mantenidas."""
    actualizar_teclas_direccion(set())


def set_mouse_down(button="left"):
    """Activa clic sostenido (izquierdo por defecto)."""
    if input_engine is None:
        return
    try:
        if not app_state.mouse_pressed:
            input_engine.mouseDown(button=button)
            app_state.mouse_pressed = True
    except Exception:
        pass


def set_mouse_up(button="left"):
    """Suelta el clic sostenido."""
    if input_engine is None:
        return
    try:
        if app_state.mouse_pressed:
            input_engine.mouseUp(button=button)
            app_state.mouse_pressed = False
    except Exception:
        pass


def click_mouse(button="right", clicks=1):
    """Ejecuta clic simple o doble clic."""
    if input_engine is None:
        return
    try:
        input_engine.click(button=button, clicks=clicks)
    except Exception:
        pass


def mover_mouse(x: int, y: int):
    """Mueve el cursor a coordenadas absolutas de pantalla con latencia mínima."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
            return
        except Exception:
            pass
    if input_engine is None:
        return
    try:
        input_engine.moveTo(int(x), int(y))
    except Exception:
        pass


def cycle_control_mode():
    """Alterna entre modo Ratón, Joystick WASD y Joystick Flechas."""
    release_all_keys()
    set_mouse_up()
    app_state.modo_arrastre = False

    orden = ["mouse", "wasd", "arrows"]
    actual = app_state.control_mode
    siguiente = orden[(orden.index(actual) + 1) % len(orden)]
    app_state.control_mode = siguiente
    print(f"[MODO CONTROL] Cambiado a: {siguiente.upper()}")
    return siguiente


def _ejecutar_accion_canonica(accion: str) -> bool:
    """Ejecuta una acción canónica ya resuelta. Retorna False si solicita salir del programa."""
    if accion == "abrir_juego":
        open_game()
    elif accion == "cerrar_juego":
        close_game()
    elif accion == "salir_programa":
        print("[SISTEMA] Cerrando aplicación por comando de voz...")
        app_state.stop_event.set()
        return False
    elif accion == "modo_raton":
        release_all_keys()
        app_state.control_mode = "mouse"
        print("[MODO] Cambiado a MOUSE (cursor + pellizco)")
    elif accion == "modo_wasd":
        set_mouse_up()
        app_state.modo_arrastre = False
        app_state.control_mode = "wasd"
        print("[MODO] Cambiado a JOYSTICK WASD")
    elif accion == "modo_flechas":
        set_mouse_up()
        app_state.modo_arrastre = False
        app_state.control_mode = "arrows"
        print("[MODO] Cambiado a JOYSTICK FLECHAS")
    elif accion == "arriba":
        hold_key_duration("up")
    elif accion == "abajo":
        hold_key_duration("down")
    elif accion == "izquierda":
        hold_key_duration("left")
    elif accion == "derecha":
        hold_key_duration("right")
    elif accion == "mover":
        app_state.control_mode = "mouse"
        app_state.modo_arrastre = True
        set_mouse_down()
        print("[ESTADO] Modo arrastre ACTIVADO")
    elif accion == "detener":
        app_state.modo_arrastre = False
        set_mouse_up()
        release_all_keys()
        print("[ESTADO] Movimiento/arrastre DETENIDO")
    elif accion == "doble_clic":
        click_mouse(button="left", clicks=2)
    elif accion == "clic":
        click_mouse(button="left", clicks=1)
    elif accion == "espacio":
        press_key("space")
    elif accion == "enter":
        press_key("enter")
    elif accion == "escape":
        press_key("esc")
    elif accion == "captura":
        take_screenshot()
    return True


_DICCIONARIO_FONETICO = {
    "arriba": "arriba", "subir": "arriba", "harina": "arriba",
    "abajo": "abajo", "bajar": "abajo", "avajo": "abajo",
    "izquierda": "izquierda", "isquierda": "izquierda",
    "derecha": "derecha",
    "mover": "mover", "arrastrar": "mover", "seguir": "mover", "avanzar": "mover",
    "detener": "detener", "parar": "detener", "alto": "detener", "quieto": "detener", "suelta": "detener", "soltar": "detener",
    "clic": "clic", "click": "clic", "clik": "clic",
    "espacio": "espacio", "despacio": "espacio", "atacar": "espacio", "saltar": "espacio", "brincar": "espacio",
    "enter": "enter", "entrar": "enter", "aceptar": "enter", "seleccionar": "enter", "confirmar": "enter",
    "escape": "escape", "pausa": "escape", "pausar": "escape", "menu": "escape", "cancelar": "escape",
    "captura": "captura", "foto": "captura", "screenshot": "captura",
}


def _normalizar_texto(texto: str) -> str:
    """Elimina tildes para comparación local robusta."""
    reemplazos = str.maketrans("áéíóúüñ", "aeiouun")
    return texto.lower().strip().translate(reemplazos)


def _detectar_accion_local(comando: str) -> str | None:
    """Coincidencia rápida sin red (<1 ms) con tolerancia a sinónimos y errores fonéticos leves."""
    import difflib
    cmd = _normalizar_texto(comando)

    if "abrir juego" in cmd or "iniciar juego" in cmd or "abre el juego" in cmd:
        return "abrir_juego"
    if "cerrar juego" in cmd or "terminar juego" in cmd or "cierra el juego" in cmd:
        return "cerrar_juego"
    if "salir" in cmd and any(w in cmd for w in ("programa", "aplicacion", "sistema")):
        return "salir_programa"
    if any(p in cmd for p in ("modo raton", "modo mouse", "usar raton", "usar mouse")):
        return "modo_raton"
    if any(p in cmd for p in ("modo teclado", "modo wasd")):
        return "modo_wasd"
    if any(p in cmd for p in ("modo flechas", "las flechitas", "usar flechas")):
        return "modo_flechas"
    if "doble clic" in cmd or "doble click" in cmd:
        return "doble_clic"

    palabras = cmd.split()
    for p in palabras:
        if p in _DICCIONARIO_FONETICO:
            return _DICCIONARIO_FONETICO[p]

    # Coincidencia aproximada (fuzzy) para errores leves de pronunciación/transcripción
    if len(palabras) <= 3:
        claves = list(_DICCIONARIO_FONETICO.keys())
        for p in palabras:
            if len(p) >= 4:
                similares = difflib.get_close_matches(p, claves, n=1, cutoff=0.80)
                if similares:
                    return _DICCIONARIO_FONETICO[similares[0]]
    return None


def ejecutar_comando(comando: str) -> bool:
    """
    Interpreta y ejecuta comandos de voz.
    Usa coincidencia rápida local y, si no coincide, consulta Gemini NLU (.env) para lenguaje natural
    o errores de pronunciación/transcripción.
    Retorna False si el comando solicita salir del programa.
    """
    if not comando:
        return True

    comando = comando.lower().strip()
    app_state.set_ultimo_comando(comando)
    print(f"[COMANDO VOZ] Recibido: '{comando}'")

    accion = _detectar_accion_local(comando)
    if accion is None and getattr(config, "GEMINI_API_KEY", ""):
        from nlu import interpretar_comando_con_gemini
        accion = interpretar_comando_con_gemini(comando)
        if accion:
            print(f"[GEMINI NLU] '{comando}' -> {accion}")
            app_state.set_ultimo_comando(f"{comando} -> {accion}")

    if accion:
        return _ejecutar_accion_canonica(accion)

    print(f"[COMANDO VOZ] Comando no reconocido: '{comando}'")
    return True


def controlar_juego_loop():
    """Bucle de escucha de voz integrado con el estado global."""
    from voz import escuchar_comando_continuo
    if getattr(config, "GEMINI_API_KEY", ""):
        from nlu import precalentar_router
        precalentar_router()
    print("[VOZ] Hilo de control por voz iniciado.")
    escuchar_comando_continuo(ejecutar_comando)
    print("[VOZ] Hilo de voz finalizado.")
