import subprocess
import psutil
from voz import reconocer_voz
import threading
import pyautogui
import datetime
import time

modo_arrastre = False

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
    global modo_arrastre

    print(f"Ejecutando comando: {comando}")

    comandos = comando.split()
    for cmd in comandos:
        if cmd == "abrir" and "juego" in comandos:
            open_game()
        elif cmd == "cerrar" and "juego" in comandos:
            close_game()
        elif cmd == "salir" and "programa" in comandos:
            print("Saliendo del programa...")
            stop_event.set()
            return False
        elif cmd == "arriba":
            pyautogui.press("up")
        elif cmd == "abajo":
            pyautogui.press("down")
        elif cmd == "izquierda":
            pyautogui.press("left")
        elif cmd == "derecha":
            pyautogui.press("right")
        elif cmd == "mover":
            modo_arrastre = True
            pyautogui.mouseDown()
            print("Modo arrastre activado.")
        elif cmd == "detener":
            modo_arrastre = False
            pyautogui.mouseUp() 
            print("Modo arrastre desactivado.")
        elif cmd == "enter":
            pyautogui.press("enter")
            print("Enter presionado.")
        elif cmd == "escape":
            pyautogui.press("esc")
            print("Escape presionado.")
        elif cmd == "captura":
            take_screenshot()
    
    return True

def iniciar_juego():
    print("Sistema iniciado")

def controlar_juego(stop_event):
    while not stop_event.is_set():
        start_time = time.time()
        comando_voz = reconocer_voz()
        print(f"Comando de voz reconocido: {comando_voz}")
        continuar = ejecutar_comando(comando_voz, stop_event)
        if not continuar:
            break
        print(f"Tiempo de ejecución: {time.time() - start_time} segundos")
