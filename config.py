"""
Configuración global del sistema de control por gestos y voz.
"""
import os
import sys


def _cargar_env_local(ruta_env: str = ".env"):
    """Carga variables desde .env sin requerir dependencias externas."""
    if not os.path.exists(ruta_env):
        return
    try:
        with open(ruta_env, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                clave = clave.strip()
                valor = valor.strip().strip('"').strip("'")
                if clave and clave not in os.environ:
                    os.environ[clave] = valor
    except Exception:
        pass


_cargar_env_local(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ==========================================
# CONFIGURACIÓN DE LA CÁMARA (LOGITECH PRO)
# ==========================================
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", 0))
# Resolución recomendada para tu Logitech Pro (720p a 60fps da el mejor equilibrio latencia/resolución)
CAMERA_WIDTH = int(os.environ.get("CAMERA_WIDTH", 1280))
CAMERA_HEIGHT = int(os.environ.get("CAMERA_HEIGHT", 720))
TARGET_FPS = int(os.environ.get("TARGET_FPS", 60))

# En Windows, usar backend DirectShow para habilitar 60 FPS reales y menor latencia
USE_DSHOW = sys.platform.startswith("win")

# ==========================================
# CONFIGURACIÓN DE INTERACCIÓN Y GESTOS
# ==========================================
# Modo de control inicial: "mouse" (cursor + pellizco) o "wasd" / "arrows" (joystick virtual)
DEFAULT_CONTROL_MODE = "mouse"

# Factor de suavizado exponencial (0.0 a 1.0)
# Valores entre 0.2 y 0.35 eliminan el temblor (jitter) sin generar retraso molesto
SMOOTHING_ALPHA = 0.30

# Zona Activa de Interacción (ROI) en porcentajes (0.0 a 1.0)
# Permite alcanzar toda la pantalla sin extender el brazo hasta los límites de la cámara
ROI_MARGIN_X = 0.15  # 15% de margen izquierdo y derecho
ROI_MARGIN_Y = 0.20  # 20% de margen superior e inferior

# Umbral de pellizco (Pinch to click / drag)
# Normalizado con respecto al tamaño aparente de la mano (distancia muñeca -> base dedo medio)
PINCH_THRESHOLD_RATIO = 0.32

# Radio de zona muerta para el modo Joystick Virtual (fracción del alto de pantalla de cámara)
JOYSTICK_DEADZONE_RATIO = 0.12

# Duración (segundos) que se mantiene pulsada una tecla al decir "arriba/abajo/izquierda/derecha"
VOICE_KEY_HOLD_SECONDS = 0.35

# MediaPipe Hands
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7

# ==========================================
# CONFIGURACIÓN DE JUEGO Y COMANDOS
# ==========================================
USER_CONFIG_FILE = "user_config.json"
DEFAULT_GAME_PATH_WIN = r"C:\Program Files (x86)\Steam\steamapps\common\Vampire Survivors\VampireSurvivors.exe"
GAME_PATH = os.environ.get("VAMPIRE_SURVIVORS_PATH", DEFAULT_GAME_PATH_WIN)
PROCESS_NAME = os.path.basename(GAME_PATH)

# ==========================================
# MOTOR DE ENTRADA (Simulación de teclado/ratón)
# ==========================================
# PyDirectInput es preferible para juegos en Windows (DirectX)
PREFER_PYDIRECTINPUT = True

# ==========================================
# NLU NATURAL CON GEMINI API (.env)
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "auto").strip()
GEMINI_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", 2.5))
GEMINI_COOLDOWN_SECONDS = float(os.environ.get("GEMINI_COOLDOWN_SECONDS", 60.0))
