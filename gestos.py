"""
Módulo de visión computacional y control por gestos.
Soporta:
- Modo MOUSE: Cursor suavizado (filtro adaptativo anti-tremor y estabilización de clic),
  ROI activa, Pellizco Izquierdo (clic/arrastre con histéresis) y Derecho.
- Modo JOYSTICK VIRTUAL (WASD / Flechas): Detección de inclinación respecto al centro con soporte de diagonales.
- Interpolador dedicado a ~120 Hz para máxima fluidez del cursor sin micro-pausas.
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


def _cursor_interpolator_loop(stop_event, paused_event, init_x: float, init_y: float):
    """Hilo de alta frecuencia (~120 Hz) para interpolar el cursor y eliminar micro-pausas."""
    cur_x, cur_y = init_x, init_y
    last_sent_x, last_sent_y = round(cur_x), round(cur_y)
    while not stop_event.is_set():
        if not paused_event.is_set() and app_state.control_mode == "mouse":
            target = app_state.get_cursor_target()
            if target is not None:
                tx, ty = target
                cur_x += (tx - cur_x) * 0.48
                cur_y += (ty - cur_y) * 0.48
                ix, iy = round(cur_x), round(cur_y)
                if ix != last_sent_x or iy != last_sent_y:
                    mover_mouse(ix, iy)
                    last_sent_x, last_sent_y = ix, iy
        time.sleep(0.008)


def _aplicar_suavizado_adaptativo(mouse_state: dict, target_x: float, target_y: float):
    """Suaviza el cursor reduciendo micro-temblores en reposo y desvío al iniciar pellizco."""
    if mouse_state.get("snap_next"):
        mouse_state["smoothed_x"] = target_x
        mouse_state["smoothed_y"] = target_y
        mouse_state["snap_next"] = False
        return

    dx = target_x - mouse_state["smoothed_x"]
    dy = target_y - mouse_state["smoothed_y"]
    dist_px = math.hypot(dx, dy)

    if time.time() < mouse_state["pinch_freeze_until"]:
        alpha = 0.05
    elif dist_px < 2.5:
        alpha = 0.08
    else:
        alpha = min(0.75, config.SMOOTHING_ALPHA + (dist_px / 220.0) * 0.45)

    mouse_state["smoothed_x"] += alpha * dx
    mouse_state["smoothed_y"] += alpha * dy


def _procesar_modo_mouse(
    index_tip: tuple,
    thumb_tip: tuple,
    middle_tip: tuple,
    roi_bounds: tuple,
    screen_size: tuple,
    mouse_state: dict,
    is_left_pinching: bool,
    is_right_pinching: bool,
    todos_extendidos: bool,
    frame,
) -> str:
    """
    Gestiona el desplazamiento del cursor en pantalla y la lógica de clics (Pellizcos y Palma abierta).
    Retorna la etiqueta descriptiva del gesto actual.
    """
    roi_x_min, roi_y_min, roi_w, roi_h = roi_bounds
    screen_w, screen_h = screen_size

    norm_x = (index_tip[0] - roi_x_min) / float(roi_w)
    norm_y = (index_tip[1] - roi_y_min) / float(roi_h)
    target_x = max(0.0, min(1.0, norm_x)) * max(1, screen_w - 1)
    target_y = max(0.0, min(1.0, norm_y)) * max(1, screen_h - 1)

    is_left_prev = mouse_state["left_pinch"]
    is_right_prev = mouse_state["right_pinch"]

    if is_left_pinching and not is_left_prev:
        mouse_state["pinch_freeze_until"] = time.time() + 0.12

    _aplicar_suavizado_adaptativo(mouse_state, target_x, target_y)
    app_state.set_cursor_target(mouse_state["smoothed_x"], mouse_state["smoothed_y"])

    if todos_extendidos and not is_left_pinching and not is_right_pinching:
        current_gesture = "Palma Abierta (Parada)"
        if is_left_prev or app_state.modo_arrastre:
            set_mouse_up()
            app_state.modo_arrastre = False
        mouse_state["left_pinch"] = False
        mouse_state["right_pinch"] = False

    elif is_left_pinching:
        current_gesture = "Pellizco Clic Izquierdo"
        cv2.line(frame, thumb_tip, index_tip, (0, 255, 0), 3)
        if not is_left_prev:
            set_mouse_down()
        mouse_state["left_pinch"] = True
        mouse_state["right_pinch"] = False

    elif is_right_pinching:
        current_gesture = "Pellizco Clic Derecho"
        cv2.line(frame, thumb_tip, middle_tip, (255, 0, 255), 3)
        if not is_right_prev:
            click_mouse(button="right")
        mouse_state["right_pinch"] = True

    else:
        current_gesture = "Apuntando (Libre)"
        cv2.line(frame, thumb_tip, index_tip, (0, 165, 255), 1)
        if is_left_prev and not app_state.modo_arrastre:
            set_mouse_up()
        mouse_state["left_pinch"] = False
        mouse_state["right_pinch"] = False

    if app_state.modo_arrastre:
        current_gesture += " + Arrastre"
        set_mouse_down()

    return current_gesture


def _procesar_modo_joystick(
    middle_mcp: tuple,
    thumb_tip: tuple,
    index_tip: tuple,
    center: tuple,
    deadzone_r: int,
    modo_actual: str,
    mouse_state: dict,
    is_left_pinching: bool,
    todos_extendidos: bool,
    frame,
) -> str:
    """
    Gestiona el Joystick Virtual calculando la desviación de la mano respecto al centro
    y activando las teclas direccionales correspondientes (WASD o Flechas).
    Retorna la etiqueta descriptiva del gesto actual.
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
        if not mouse_state["left_pinch"]:
            press_key("space")
        mouse_state["left_pinch"] = True
    else:
        mouse_state["left_pinch"] = False

    return current_gesture


def _put_text_shadow(frame, text: str, org: tuple, scale: float, color: tuple, thickness: int = 2):
    """Dibuja texto con contorno oscuro para mantener legibilidad sobre fondos claros."""
    cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def _dibujar_hud(
    frame,
    fps: float,
    modo_actual: str,
    current_gesture: str,
    paused: bool,
    roi_bounds: tuple,
    center: tuple,
    deadzone_r: int,
):
    """Renderiza las guías visuales en pantalla y el panel de información en vivo (HUD)."""
    roi_x_min, roi_y_min, roi_x_max, roi_y_max = roi_bounds
    center_x, center_y = center

    if modo_actual == "mouse":
        cv2.rectangle(frame, (roi_x_min, roi_y_min), (roi_x_max, roi_y_max), (255, 200, 0), 2)
        _put_text_shadow(frame, "Zona Activa (Mouse)", (roi_x_min + 5, roi_y_min - 8), 0.5, (255, 200, 0), 1)
    else:
        cv2.circle(frame, (center_x, center_y), deadzone_r, (255, 200, 0), 2)
        _put_text_shadow(frame, f"Joystick ({modo_actual.upper()})", (center_x - 65, center_y - deadzone_r - 10),
                         0.55, (255, 200, 0), 2)

    estado_pausa = " | PAUSADO [P]" if paused else ""
    hud_text = [
        (f"FPS: {fps:.1f} | Modo [M]: {modo_actual.upper()}{estado_pausa}", (0, 255, 255)),
        (f"Gesto: {current_gesture}", (0, 255, 180) if not paused else (0, 140, 255)),
        (f"Arrastre [D]: {'ON' if app_state.modo_arrastre else 'OFF'}", (0, 255, 255)),
        (f"Ultimo Voz: {app_state.ultimo_comando}", (255, 255, 255)),
        ("Controles: [M] Modo | [D] Arrastre | [P] Pausa | [Q]/[X] Salir", (200, 220, 255)),
    ]
    for i, (text, color) in enumerate(hud_text):
        _put_text_shadow(frame, text, (15, 28 + i * 25), 0.58, color, 2)


def _manejar_tecla_ventana(key: int, stop_event, paused_event, mouse_state: dict) -> bool:
    """Procesa atajos de teclado en la ventana OpenCV. Retorna False si debe cerrarse."""
    if key == ord("q"):
        print("[SISTEMA] Saliendo por tecla 'q'...")
        stop_event.set()
        return False
    if key == ord("m"):
        cycle_control_mode()
        mouse_state["snap_next"] = True
    elif key == ord("d"):
        nuevo = not app_state.modo_arrastre
        app_state.modo_arrastre = nuevo
        if nuevo:
            set_mouse_down()
        else:
            set_mouse_up()
        print(f"[ESTADO] Arrastre manual: {'ON' if nuevo else 'OFF'}")
    elif key == ord("p"):
        if paused_event.is_set():
            paused_event.clear()
            mouse_state["snap_next"] = True
            print("[GESTOS] Control REANUDADO.")
        else:
            paused_event.set()
            app_state.modo_arrastre = False
            set_mouse_up()
            release_all_keys()
            mouse_state["left_pinch"] = False
            mouse_state["right_pinch"] = False
            print("[GESTOS] Control PAUSADO (presiona 'p' para reanudar).")
    return True


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
        min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
    )
    mp_draw = mp.solutions.drawing_utils

    screen_w, screen_h = obtener_tamano_pantalla()
    paused_event = threading.Event()
    mouse_state = {
        "smoothed_x": screen_w / 2.0,
        "smoothed_y": screen_h / 2.0,
        "left_pinch": False,
        "right_pinch": False,
        "pinch_freeze_until": 0.0,
        "snap_next": True,
    }

    interp_thread = threading.Thread(
        target=_cursor_interpolator_loop,
        args=(stop_event, paused_event, mouse_state["smoothed_x"], mouse_state["smoothed_y"]),
        name="HiloCursor120Hz",
        daemon=True,
    )
    interp_thread.start()

    prev_time = time.time()
    fps = 0.0
    prev_mode = app_state.control_mode

    print("[GESTOS] Activo. Teclas: [M] Modo | [D] Arrastre | [P] Pausa | [Q]/[X] Salir")
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

            modo_actual = app_state.control_mode
            if modo_actual == "mouse" and prev_mode != "mouse":
                mouse_state["snap_next"] = True
            prev_mode = modo_actual

            paused = paused_event.is_set()
            current_gesture = "Control Pausado [P]" if paused else "Sin Mano"

            if not paused:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb_frame.flags.writeable = False
                results = hands_detector.process(rgb_frame)
                rgb_frame.flags.writeable = True

                hand_detected = results.multi_hand_landmarks is not None
                app_state.manos_detectadas = 1 if hand_detected else 0

                if hand_detected:
                    hand_landmarks = results.multi_hand_landmarks[0]
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    lm = hand_landmarks.landmark

                    wrist = (int(lm[0].x * frame_w), int(lm[0].y * frame_h))
                    thumb_tip = (int(lm[4].x * frame_w), int(lm[4].y * frame_h))
                    index_tip = (int(lm[8].x * frame_w), int(lm[8].y * frame_h))
                    middle_mcp = (int(lm[9].x * frame_w), int(lm[9].y * frame_h))
                    middle_tip = (int(lm[12].x * frame_w), int(lm[12].y * frame_h))
                    ring_tip = (int(lm[16].x * frame_w), int(lm[16].y * frame_h))
                    pinky_tip = (int(lm[20].x * frame_w), int(lm[20].y * frame_h))

                    hand_scale = max(20.0, calcular_distancia(wrist, middle_mcp))
                    todos_extendidos = (
                        index_tip[1] < lm[6].y * frame_h and
                        middle_tip[1] < lm[10].y * frame_h and
                        ring_tip[1] < lm[14].y * frame_h and
                        pinky_tip[1] < lm[18].y * frame_h
                    )

                    umbral_on = config.PINCH_THRESHOLD_RATIO
                    umbral_off = umbral_on * 1.28
                    ratio_left = calcular_distancia(thumb_tip, index_tip) / hand_scale
                    ratio_right = calcular_distancia(thumb_tip, middle_tip) / hand_scale
                    is_left_pinching = ratio_left < (umbral_off if mouse_state["left_pinch"] else umbral_on)
                    is_right_pinching = ratio_right < (umbral_off if mouse_state["right_pinch"] else umbral_on)

                    if modo_actual == "mouse":
                        current_gesture = _procesar_modo_mouse(
                            index_tip, thumb_tip, middle_tip,
                            (roi_x_min, roi_y_min, roi_w, roi_h),
                            (screen_w, screen_h),
                            mouse_state, is_left_pinching, is_right_pinching, todos_extendidos, frame,
                        )
                    else:
                        current_gesture = _procesar_modo_joystick(
                            middle_mcp, thumb_tip, index_tip,
                            (center_x, center_y), deadzone_r, modo_actual,
                            mouse_state, is_left_pinching, todos_extendidos, frame,
                        )
                else:
                    if not app_state.modo_arrastre and mouse_state["left_pinch"]:
                        set_mouse_up()
                    mouse_state["left_pinch"] = False
                    mouse_state["right_pinch"] = False
                    release_all_keys()
            else:
                app_state.manos_detectadas = 0

            app_state.gesto_actual = current_gesture

            curr_time = time.time()
            inst_fps = 1.0 / max(1e-5, (curr_time - prev_time))
            fps = inst_fps if fps == 0.0 else (fps * 0.9 + inst_fps * 0.1)
            prev_time = curr_time
            app_state.fps_camara = fps

            _dibujar_hud(
                frame, fps, modo_actual, current_gesture, paused,
                (roi_x_min, roi_y_min, roi_x_max, roi_y_max),
                (center_x, center_y), deadzone_r,
            )

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key != 255 and not _manejar_tecla_ventana(key, stop_event, paused_event, mouse_state):
                break

            try:
                if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                    print("[SISTEMA] Ventana cerrada por el usuario [X]. Saliendo...")
                    stop_event.set()
                    break
            except cv2.error:
                stop_event.set()
                break

    finally:
        set_mouse_up()
        release_all_keys()
        interp_thread.join(timeout=0.5)
        hands_detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print("[GESTOS] Recursos de cámara y MediaPipe liberados.")
