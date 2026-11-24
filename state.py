"""
Módulo de estado compartido entre hilos (Gestos, Voz, Interfaz).
Resuelve la desincronización de variables primitivas entre módulos en Python.
"""
import threading
import os
import config


class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.stop_event = threading.Event()

        # Modo arrastre (clic izquierdo sostenido continuo)
        self._modo_arrastre = False

        # Estado actual de clic físico (mouseDown simulado)
        self._mouse_pressed = False

        # Modo de control de movimiento: "mouse", "wasd", "arrows"
        self._control_mode = config.DEFAULT_CONTROL_MODE

        # Teclas mantenidas actualmente (para modo Joystick Virtual)
        self._held_keys = set()

        # Ruta y proceso del juego seleccionado
        self._game_path = config.GAME_PATH
        self._process_name = os.path.basename(config.GAME_PATH)

        # Último comando de voz detectado
        self.ultimo_comando = "Ninguno"

        # Objetivo del cursor para interpolación suave de alta frecuencia (120 Hz)
        self._cursor_target = None

        # Métricas de rendimiento
        self.fps_camara = 0.0
        self.manos_detectadas = 0
        self.gesto_actual = "Ninguno"

    @property
    def modo_arrastre(self) -> bool:
        with self._lock:
            return self._modo_arrastre

    @modo_arrastre.setter
    def modo_arrastre(self, valor: bool):
        with self._lock:
            self._modo_arrastre = valor

    @property
    def mouse_pressed(self) -> bool:
        with self._lock:
            return self._mouse_pressed

    @mouse_pressed.setter
    def mouse_pressed(self, valor: bool):
        with self._lock:
            self._mouse_pressed = valor

    @property
    def control_mode(self) -> str:
        with self._lock:
            return self._control_mode

    @control_mode.setter
    def control_mode(self, mode: str):
        with self._lock:
            if mode in ("mouse", "wasd", "arrows"):
                self._control_mode = mode

    @property
    def game_path(self) -> str:
        with self._lock:
            return self._game_path

    @game_path.setter
    def game_path(self, path: str):
        with self._lock:
            self._game_path = path
            self._process_name = os.path.basename(path) if path else ""

    @property
    def process_name(self) -> str:
        with self._lock:
            return self._process_name

    def get_held_keys(self) -> set:
        with self._lock:
            return set(self._held_keys)

    def set_held_keys(self, keys: set):
        with self._lock:
            self._held_keys = set(keys)

    def set_ultimo_comando(self, comando: str):
        with self._lock:
            self.ultimo_comando = comando

    def set_cursor_target(self, x: float, y: float):
        with self._lock:
            self._cursor_target = (float(x), float(y))

    def get_cursor_target(self):
        with self._lock:
            return self._cursor_target


# Instancia global compartida por todos los módulos
app_state = AppState()
