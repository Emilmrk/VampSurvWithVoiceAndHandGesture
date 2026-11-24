"""
Módulo de visión computacional y control por gestos.
Soporta:
- Modo MOUSE: Cursor suavizado (EMA adaptativo), ROI activa, Pellizco Izquierdo (clic/arrastre) y Derecho.
- Modo JOYSTICK VIRTUAL (WASD / Flechas): Detección de inclinación respecto al centro con soporte de diagonales.
- Interpolador dedicado a 120 Hz para máxima fluidez del cursor sin micro-pausas.
"""
import math
import threading
import time
import cv2
import mediapipe as mp

import config
from state import app_state
from game import (
    mover_mouse,
    set_mouse_down,
    set_mouse_up,
    click_mouse,
    press_key,
    actualizar_teclas_direccion,
    release_all_keys,
    cycle_control_mode,
)

WINDOW_NAME = "Control Gestual - Vampire Survivors"


def es_wsl() -> bool:
    """Detecta si el entorno actual es Windows Subsystem for Linux (WSL)."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def calcular_distancia(p1: tuple, p2: tuple) -> float:
    """Calcula la distancia euclidiana entre dos puntos (x, y)."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def inicializar_camara():
    """Abre y configura la cámara probando índices y optimizando para 60 FPS nativos."""
    indices_a_probar = [config.CAMERA_INDEX] + [i for i in range(4) if i != config.CAMERA_INDEX]
    cap = None
    indice_encontrado = None

    for idx in indices_a_probar:
        if config.USE_DSHOW:
            temp_cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        else:
            temp_cap = cv2.VideoCapture(idx)

        if temp_cap.isOpened():
            ret, _ = temp_cap.read()
            if ret:
                cap = temp_cap
                indice_encontrado = idx
                break
            temp_cap.release()

    if cap is None:
        print("\n" + "=" * 65)
        print("[ERROR CRÍTICO] No se detectó ninguna cámara de video disponible.")
        if es_wsl():
            print("\n[DIAGNÓSTICO: ENTORNO WSL2 DETECTADO]")
            print("Ejecuta el proyecto directamente en Windows desde PowerShell: python main.py")
        print("=" * 65 + "\n")
        return None

    # Forzar MJPG antes de resolución/FPS para desbloquear 60 FPS reales en Windows DirectShow
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[CAM] Cámara detectada en índice {indice_encontrado}: {actual_w}x{actual_h} @ {actual_fps:.1f} FPS")
    return cap


def obtener_tamano_pantalla() -> tuple:
    """Obtiene la resolución de pantalla del monitor de forma segura."""
    try:
        import pyautogui
        return pyautogui.size()
    except Exception:
        return (1920, 1080)


def _cursor_interpolator_loop(stop_event, init_x: float, init_y: float):
    """Hilo de alta frecuencia (120 Hz) para interpolar el cursor y eliminar micro-pausas."""
    cur_x, cur_y = init_x, init_y
    last_sent_x, last_sent_y = int(cur_x), int(cur_y)
    while not stop_event.is_set():
        target = app_state.get_cursor_target()
        if target is not None and app_state.control_mode == "mouse":
            tx, ty = target
            cur_x += (tx - cur_x) * 0.35
            cur_y += (ty - cur_y) * 0.35
            ix, iy = int(cur_x), int(cur_y)
            if ix != last_sent_x or iy != last_sent_y:
                mover_mouse(ix, iy)
                last_sent_x, last_sent_y = ix, iy
        time.sleep(0.008)


def _procesar_modo_mouse(
    index_tip: tuple,
    thumb_tip: tuple,
    middle_tip: tuple,
    roi_bounds: tuple,
    screen_size: tuple,
    smoothed_pos: tuple,
    pinching_states: tuple,
    is_left_pinching: bool,
    is_right_pinching: bool,
    todos_extendidos: bool,
    frame
) -> tuple:
    """
    Gestiona el desplazamiento del cursor en pantalla y la lógica de clics (Pellizcos y Palma abierta).
    Retorna (current_gesture, smoothed_x, smoothed_y, is_left_pinching_prev, is_right_pinching_prev).
    """
    roi_x_min, roi_y_min, roi_w, roi_h = roi_bounds
    screen_w, screen_h = screen_size
    smoothed_x, smoothed_y = smoothed_pos
    is_left_pinching_prev, is_right_pinching_prev = pinching_states

    norm_x = (index_tip[0] - roi_x_min) / float(roi_w)
    norm_y = (index_tip[1] - roi_y_min) / float(roi_h)
    clamped_x = max(0.0, min(1.0, norm_x))
    clamped_y = max(0.0, min(1.0, norm_y))

    target_screen_x = clamped_x * screen_w
    target_screen_y = clamped_y * screen_h

    # Suavizado adaptativo: mayor filtro en reposo, mayor respuesta en movimiento
    dx_s = target_screen_x - smoothed_x
    dy_s = target_screen_y - smoothed_y
    dist_px = math.hypot(dx_s, dy_s)
    alpha = config.SMOOTHING_ALPHA if dist_px < 40.0 else min(0.65, config.SMOOTHING_ALPHA * 1.8)
    smoothed_x += alpha * dx_s
    smoothed_y += alpha * dy_s

    app_state.set_cursor_target(smoothed_x, smoothed_y)

    if todos_extendidos and not is_left_pinching and not is_right_pinching:
        current_gesture = "Palma Abierta (Parada)"
        if is_left_pinching_prev or app_state.modo_arrastre:
            set_mouse_up()
            app_state.modo_arrastre = False
        is_left_pinching_prev = False
        is_right_pinching_prev = False

    elif is_left_pinching:
        current_gesture = "Pellizco Clic Izquierdo"
        cv2.line(frame, thumb_tip, index_tip, (0, 255, 0), 3)
        if not is_left_pinching_prev:
            set_mouse_down()
        is_left_pinching_prev = True

    elif is_right_pinching:
        current_gesture = "Pellizco Clic Derecho"
        cv2.line(frame, thumb_tip, middle_tip, (255, 0, 255), 3)
        if not is_right_pinching_prev:
            click_mouse(button="right")
        is_right_pinching_prev = True

    else:
        current_gesture = "Apuntando (Libre)"
        cv2.line(frame, thumb_tip, index_tip, (0, 165, 255), 1)
        if is_left_pinching_prev and not app_state.modo_arrastre:
            set_mouse_up()
        is_left_pinching_prev = False
        is_right_pinching_prev = False

    if app_state.modo_arrastre:
        current_gesture += " + Arrastre"
        set_mouse_down()

    return current_gesture, smoothed_x, smoothed_y, is_left_pinching_prev, is_right_pinching_prev


def _procesar_modo_joystick(
    middle_mcp: tuple,
    thumb_tip: tuple,
    index_tip: tuple,
    center: tuple,
    deadzone_r: int,
    modo_actual: str,
    is_left_pinching_prev: bool,
    is_left_pinching: bool,
    todos_extendidos: bool,
    frame
) -> tuple:
    """
    Gestiona el Joystick Virtual calculando la desviación de la mano respecto al centro
    y activando las teclas direccionales correspondientes (WASD o Flechas).
    Retorna (current_gesture, is_left_pinching_prev).
    """
    key_map = (
        {"up": "w", "down": "s", "left": "a", "right": "d"}
        if modo_actual == "wasd"
        else {"up": "up", "down": "down", "left": "left", "right": "right"}
    )

    center_x, center_y = center
    dx = middle_mcp[0] - center_x
    dy = middle_mcp[1] - center_y
    dist_center = math.hypot(dx, dy)

    cv2.line(frame, center, middle_mcp, (0, 255, 255), 2)

    if todos_extendidos and not is_left_pinching:
        release_all_keys()
        current_gesture = "Palma Abierta (Neutro)"
    elif dist_center > deadzone_r:
        teclas = set()
        umbral_eje = deadzone_r * 0.55
        if dy < -umbral_eje:
            teclas.add(key_map["up"])
        elif dy > umbral_eje:
            teclas.add(key_map["down"])
        if dx < -umbral_eje:
            teclas.add(key_map["left"])
        elif dx > umbral_eje:
            teclas.add(key_map["right"])

        actualizar_teclas_direccion(teclas)
        current_gesture = "Teclas: " + "+".join(sorted(k.upper() for k in teclas)) if teclas else "Centro"
    else:
        release_all_keys()
        current_gesture = "Joystick Centro (Neutro)"

    if is_left_pinching:
        cv2.line(frame, thumb_tip, index_tip, (0, 255, 0), 3)
        if not is_left_pinching_prev:
            press_key("space")
        is_left_pinching_prev = True
    else:
        is_left_pinching_prev = False

    return current_gesture, is_left_pinching_prev


def _dibujar_hud(
    frame,
    fps: float,
    modo_actual: str,
    current_gesture: str,
    roi_bounds: tuple,
    center: tuple,
    deadzone_r: int
):
    """Renderiza las guías visuales en pantalla y el panel de información en vivo (HUD)."""
    roi_x_min, roi_y_min, roi_x_max, roi_y_max = roi_bounds
    center_x, center_y = center

    if modo_actual == "mouse":
        cv2.rectangle(frame, (roi_x_min, roi_y_min), (roi_x_max, roi_y_max), (255, 200, 0), 2)
        cv2.putText(frame, "Zona Activa (Mouse)", (roi_x_min + 5, roi_y_min - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
    else:
        cv2.circle(frame, (center_x, center_y), deadzone_r, (255, 200, 0), 2)
        cv2.putText(frame, f"Joystick ({modo_actual.upper()})", (center_x - 65, center_y - deadzone_r - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 2)

    hud_text = [
        f"FPS: {fps:.1f} | Modo [M]: {modo_actual.upper()}",
        f"Gesto: {current_gesture}",
        f"Arrastre [D]: {'ON' if app_state.modo_arrastre else 'OFF'}",
        f"Ultimo Voz: {app_state.ultimo_comando}",
        "Salir: [Q] o cerrar ventana [X]"
    ]
    for i, text in enumerate(hud_text):
        cv2.putText(frame, text, (15, 28 + i * 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)


def reconocer_gestos(stop_event=None):
    """Bucle principal de procesamiento de visión computacional y control gestual."""
    if stop_event is None:
        stop_event = app_state.stop_event

    cap = inicializar_camara()
    if cap is None:
        stop_event.set()
        return

    mp_hands = mp.solutions.hands
    hands_detector = mp_hands.Hands(
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE
    )
    mp_draw = mp.solutions.drawing_utils

    screen_w, screen_h = obtener_tamano_pantalla()
    smoothed_x, smoothed_y = screen_w / 2.0, screen_h / 2.0

    interp_thread = threading.Thread(
        target=_cursor_interpolator_loop,
        args=(stop_event, smoothed_x, smoothed_y),
        name="HiloCursor120Hz",
        daemon=True,
    )
    interp_thread.start()

    is_left_pinching_prev = False
    is_right_pinching_prev = False
    prev_time = time.time()
    fps = 0.0

    print("[GESTOS] Activo. Teclas en ventana: [Q] Salir | [M] Cambiar Modo | [D] Arrastre | [X] Cerrar")
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)
            frame_h, frame_w, _ = frame.shape

            roi_x_min = int(frame_w * config.ROI_MARGIN_X)
            roi_x_max = int(frame_w * (1.0 - config.ROI_MARGIN_X))
            roi_y_min = int(frame_h * config.ROI_MARGIN_Y)
            roi_y_max = int(frame_h * (1.0 - config.ROI_MARGIN_Y))
            roi_w = max(1, roi_x_max - roi_x_min)
            roi_h = max(1, roi_y_max - roi_y_min)

            center_x, center_y = frame_w // 2, frame_h // 2
            deadzone_r = int(frame_h * config.JOYSTICK_DEADZONE_RATIO)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            results = hands_detector.process(rgb_frame)
            rgb_frame.flags.writeable = True

            hand_detected = results.multi_hand_landmarks is not None
            app_state.manos_detectadas = 1 if hand_detected else 0
            current_gesture = "Sin Mano"
            modo_actual = app_state.control_mode

            if hand_detected:
                hand_landmarks = results.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                landmarks = hand_landmarks.landmark

                wrist = (int(landmarks[0].x * frame_w), int(landmarks[0].y * frame_h))
                thumb_tip = (int(landmarks[4].x * frame_w), int(landmarks[4].y * frame_h))
                index_tip = (int(landmarks[8].x * frame_w), int(landmarks[8].y * frame_h))
                middle_mcp = (int(landmarks[9].x * frame_w), int(landmarks[9].y * frame_h))
                middle_tip = (int(landmarks[12].x * frame_w), int(landmarks[12].y * frame_h))
                ring_tip = (int(landmarks[16].x * frame_w), int(landmarks[16].y * frame_h))
                pinky_tip = (int(landmarks[20].x * frame_w), int(landmarks[20].y * frame_h))

                hand_scale = max(20.0, calcular_distancia(wrist, middle_mcp))
                todos_extendidos = (
                    index_tip[1] < landmarks[6].y * frame_h and
                    middle_tip[1] < landmarks[10].y * frame_h and
                    ring_tip[1] < landmarks[14].y * frame_h and
                    pinky_tip[1] < landmarks[18].y * frame_h
                )

                is_left_pinching = (calcular_distancia(thumb_tip, index_tip) / hand_scale) < config.PINCH_THRESHOLD_RATIO
                is_right_pinching = (calcular_distancia(thumb_tip, middle_tip) / hand_scale) < config.PINCH_THRESHOLD_RATIO

                if modo_actual == "mouse":
                    current_gesture, smoothed_x, smoothed_y, is_left_pinching_prev, is_right_pinching_prev = (
                        _procesar_modo_mouse(
                            index_tip, thumb_tip, middle_tip,
                            (roi_x_min, roi_y_min, roi_w, roi_h),
                            (screen_w, screen_h),
                            (smoothed_x, smoothed_y),
                            (is_left_pinching_prev, is_right_pinching_prev),
                            is_left_pinching, is_right_pinching, todos_extendidos, frame
                        )
                    )
                else:
                    current_gesture, is_left_pinching_prev = _procesar_modo_joystick(
                        middle_mcp, thumb_tip, index_tip,
                        (center_x, center_y), deadzone_r, modo_actual,
                        is_left_pinching_prev, is_left_pinching, todos_extendidos, frame
                    )
            else:
                if not app_state.modo_arrastre and is_left_pinching_prev:
                    set_mouse_up()
                    is_left_pinching_prev = False
                release_all_keys()

            app_state.gesto_actual = current_gesture

            curr_time = time.time()
            fps = 1.0 / max(1e-5, (curr_time - prev_time))
            prev_time = curr_time
            app_state.fps_camara = fps

            _dibujar_hud(
                frame, fps, modo_actual, current_gesture,
                (roi_x_min, roi_y_min, roi_x_max, roi_y_max),
                (center_x, center_y), deadzone_r
            )

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("[SISTEMA] Saliendo por tecla 'q'...")
                stop_event.set()
                break
            elif key == ord('m'):
                cycle_control_mode()
            elif key == ord('d'):
                nuevo = not app_state.modo_arrastre
                app_state.modo_arrastre = nuevo
                if nuevo:
                    set_mouse_down()
                else:
                    set_mouse_up()
                print(f"[ESTADO] Arrastre manual: {'ON' if nuevo else 'OFF'}")

            # Botón 'X' de la ventana
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                print("[SISTEMA] Ventana cerrada por el usuario [X]. Saliendo...")
                stop_event.set()
                break

    finally:
        set_mouse_up()
        release_all_keys()
        hands_detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print("[GESTOS] Recursos de cámara y MediaPipe liberados.")
