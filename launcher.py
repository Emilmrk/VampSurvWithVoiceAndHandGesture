"""
Módulo de gestión y lanzamiento de juegos.
Maneja la detección de rutas, selección interactiva de ejecutables (CLI / GUI)
y persistencia de configuración de usuario en user_config.json.
"""
import json
import os
import subprocess
import sys
import psutil

import config
from state import app_state


def cargar_config_usuario() -> dict:
    """Carga preferencias guardadas en user_config.json si existe."""
    if os.path.exists(config.USER_CONFIG_FILE):
        try:
            with open(config.USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "game_path" in data:
                app_state.game_path = data["game_path"] or ""
            if data.get("control_mode") in ("mouse", "wasd", "arrows"):
                app_state.control_mode = data["control_mode"]
            return data
        except Exception as e:
            print(f"[CONFIG] No se pudo leer {config.USER_CONFIG_FILE}: {e}")
    return {}


def guardar_config_usuario(free_mode: bool = False):
    """Guarda la ruta del juego y preferencias actuales en user_config.json."""
    try:
        with open(config.USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "game_path": app_state.game_path,
                "control_mode": app_state.control_mode,
                "free_mode": free_mode,
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[CONFIG] No se pudo guardar {config.USER_CONFIG_FILE}: {e}")


def buscar_rutas_steam_comunes() -> str | None:
    """Busca Vampire Survivors en rutas típicas de bibliotecas de Steam."""
    if sys.platform.startswith("win"):
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
    else:
        candidato = os.path.expanduser("~/.local/share/Steam/steamapps/common/Vampire Survivors/VampireSurvivors.exe")
        if os.path.exists(candidato):
            return candidato
    return None


def _seleccionar_archivo_grafico() -> str | None:
    """Abre un selector nativo con tkinter si hay entorno gráfico disponible."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        tipos = [("Ejecutables", "*.exe"), ("Todos los archivos", "*.*")] if sys.platform.startswith("win") else [("Todos los archivos", "*.*")]
        ruta = filedialog.askopenfilename(
            title="Selecciona el ejecutable del juego",
            filetypes=tipos,
        )
        root.destroy()
        return ruta
    except Exception:
        return None


def verificar_o_configurar_juego(forzar_menu: bool = False) -> bool:
    """
    Verifica la existencia del juego en la ruta configurada.
    Permite ingresar otra ruta, elegir un ejecutable con explorador gráfico,
    continuar en Modo Libre o cancelar la ejecución.
    Retorna True para continuar o False para salir.
    """
    user_cfg = cargar_config_usuario()
    ruta_actual = app_state.game_path

    if user_cfg.get("free_mode") and not forzar_menu:
        print("[JUEGO] Modo Libre activo (control de PC sin juego; usa 'python main.py --config' para cambiar).")
        return True

    # Auto-detección inicial si la ruta configurada no existe
    if (not ruta_actual or not os.path.exists(ruta_actual)) and not forzar_menu:
        encontrado = buscar_rutas_steam_comunes()
        if encontrado:
            print(f"[JUEGO] Auto-detectado en: {encontrado}")
            app_state.game_path = encontrado
            guardar_config_usuario(free_mode=False)
            return True

    if ruta_actual and os.path.exists(ruta_actual) and not forzar_menu:
        print(f"[JUEGO] Ruta verificada correctamente: {ruta_actual}")
        return True

    while True:
        print("\n" + "-" * 65)
        if not app_state.game_path or not os.path.exists(app_state.game_path):
            objetivo_txt = app_state.game_path or "(sin ruta configurada)"
            print(f"[AVISO] No se encontró el juego en:\n  -> {objetivo_txt}")
        else:
            print(f"[CONFIGURACIÓN DE JUEGO] Ruta actual:\n  -> {app_state.game_path}")

        print("\n¿Qué deseas hacer?")
        print("  1. Ingresar manualmente la ruta del juego (.exe o ejecutable)")
        print("  2. Seleccionar otro juego con el explorador de archivos")
        print("  3. Continuar sin abrir ningún juego (Modo Libre / controlar PC)")
        print("  4. Cancelar y salir del programa")

        try:
            opcion = input("\nElige una opción (1-4) [3]: ").strip() or "3"
        except (EOFError, KeyboardInterrupt):
            return False

        if opcion == "1":
            try:
                nueva_ruta = input("Pega la ruta completa del juego: ").strip().strip('"').strip("'")
            except (EOFError, KeyboardInterrupt):
                return False
            if not nueva_ruta:
                continue
            if os.path.exists(nueva_ruta):
                app_state.game_path = nueva_ruta
                guardar_config_usuario(free_mode=False)
                print(f"[JUEGO] Ruta guardada: {nueva_ruta}")
                return True
            print(f"[ERROR] El archivo no existe en: {nueva_ruta}")

        elif opcion == "2":
            ruta_gui = _seleccionar_archivo_grafico()
            if ruta_gui and os.path.exists(ruta_gui):
                app_state.game_path = ruta_gui
                guardar_config_usuario(free_mode=False)
                print(f"[JUEGO] Juego guardado: {ruta_gui}")
                return True
            print("[AVISO] No se seleccionó archivo o no hay entorno gráfico.")

        elif opcion == "3":
            app_state.game_path = ""
            guardar_config_usuario(free_mode=True)
            print("[SISTEMA] Modo Libre guardado (sin ejecutable automático). Usa --config para cambiar.")
            return True

        elif opcion == "4":
            print("[SISTEMA] Inicio cancelado por el usuario.")
            return False

        else:
            print("Opción no válida. Elige entre 1 y 4.")


def is_process_running(process_name: str | None = None) -> bool:
    """Comprueba si el proceso del juego está en ejecución."""
    objetivo = process_name or app_state.process_name
    if not objetivo:
        return False
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == objetivo.lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def open_game():
    """Lanza el ejecutable configurado si existe y no está corriendo."""
    ruta = app_state.game_path
    proceso = app_state.process_name
    if not ruta or not os.path.exists(ruta):
        print(f"[JUEGO] No hay un ejecutable válido configurado ({ruta or 'Modo Libre'}).")
        print("[JUEGO] Inicia con 'python main.py --config' para elegir otro juego.")
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
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == proceso.lower():
                proc.terminate()
                print(f"[JUEGO] Cerrando {proceso}...")
                encontrado = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not encontrado:
        print(f"[JUEGO] '{proceso}' no está en ejecución.")
