import subprocess
import psutil
from voz import reconocer_voz
import threading
import pyautogui
import datetime

modo_arrastre = False  # Variable global para el modo de arrastre

def is_process_running(process_name):
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == process_name:
            return True
    return False

def open_game():
    if not is_process_running("VampireSurvivors.exe"):
        game_path = "E:\\Steam\\steamapps\\common\\Vampire Survivors\\VampireSurvivors.exe"
        subprocess.Popen(game_path)
        print("Abriendo Vampire Survivors...")
    else:
        print("El juego ya está en ejecución.")

def close_game():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == "VampireSurvivors.exe":
            proc.terminate()
            print("Cerrando Vampire Survivors...")
            break
    else:
        print("El juego no está en ejecución.")

def take_screenshot():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = f"screenshot_{timestamp}.png"
    pyautogui.screenshot(screenshot_path)
    print(f"Captura de pantalla guardada como {screenshot_path}")

def ejecutar_comando(comando, stop_event):
    global modo_arrastre  # Declarar la variable global

    print(f"Ejecutando comando: {comando}")  # Mensaje de depuración
    
    if "abrir juego" in comando:
        open_game()
    elif "cerrar juego" in comando:
        close_game()
    elif "salir del programa" in comando:
        print("Saliendo del programa...")
        stop_event.set()  # Señal para detener los hilos
        return False
    elif "arriba" in comando:
        pyautogui.press("up")
    elif "abajo" in comando:
        pyautogui.press("down")
    elif "izquierda" in comando:
        pyautogui.press("left")
    elif "derecha" in comando:
        pyautogui.press("right")
    elif "mover" in comando:
        modo_arrastre = True
        pyautogui.mouseDown()  # Activar el clic del ratón
        print("Modo arrastre activado.")
        print(f"Estado de modo_arrastre: {modo_arrastre}")  # Mensaje de depuración
    elif "detener" in comando:
        modo_arrastre = False
        pyautogui.mouseUp()  # Asegurarse de soltar el arrastre si estaba activado
        print("Modo arrastre desactivado.")
        print(f"Estado de modo_arrastre: {modo_arrastre}")  # Mensaje de depuración
    elif "enter" in comando:
        pyautogui.press("enter")
        print("Enter presionado.")
    elif "escape" in comando:
        pyautogui.press("esc")
        print("Escape presionado.")
    elif "captura" in comando:
        take_screenshot()
    return True

def iniciar_juego():
    print("Sistema iniciado")
    # Aquí podrías iniciar cualquier otra configuración inicial

def controlar_juego(stop_event):
    while not stop_event.is_set():
        comando_voz = reconocer_voz()
        print(f"Comando de voz reconocido: {comando_voz}")  # Este mensaje imprime el comando reconocido
        continuar = ejecutar_comando(comando_voz, stop_event)
        if not continuar:
            break
