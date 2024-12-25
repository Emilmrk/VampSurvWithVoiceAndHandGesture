import cv2
import mediapipe as mp
import pyautogui
import threading
from game import modo_arrastre  # Import the drag mode

def reconocer_gestos(stop_event):
    print("Función reconocer_gestos iniciada.")  # Mensaje de depuración
    print("Intentando abrir la cámara...")  # Mensaje de depuración
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara.")  # Mensaje de depuración para fallo de apertura de cámara
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    hand_detector = mp.solutions.hands.Hands(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7)
    drawing_utils = mp.solutions.drawing_utils
    screen_width, screen_height = pyautogui.size()

    index_x, index_y, thumb_x, thumb_y = 0, 0, 0, 0
    frame_counter = 0
    process_every_n_frames = 3

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print("Error: No se pudo leer el frame de la cámara.")  # Mensaje de depuración para fallo de lectura de frame
            break

        frame_counter += 1

        if frame_counter % process_every_n_frames == 0:
            frame = cv2.flip(frame, 1)
            frame_height, frame_width, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            output = hand_detector.process(rgb_frame)
            hands = output.multi_hand_landmarks

            if hands:
                print("Manos detectadas.")  # Mensaje de depuración
                for hand in hands:
                    drawing_utils.draw_landmarks(frame, hand)
                    landmarks = hand.landmark
                    for id, landmark in enumerate(landmarks):
                        x = int(landmark.x * frame_width)
                        y = int(landmark.y * frame_height)
                        
                        if id == 8:  # Índice
                            index_x = screen_width / frame_width * x
                            index_y = screen_height / frame_height * y
                            print(f"Coordenadas índice: ({index_x}, {index_y})")  # Mensaje de depuración

                        if id == 4:  # Pulgar
                            thumb_x = screen_width / frame_width * x
                            thumb_y = screen_height / frame_height * y
                            print(f"Coordenadas pulgar: ({thumb_x}, {thumb_y})")  # Mensaje de depuración

                    # Siempre mueve el cursor
                    safe_margin = 50  # Margen de seguridad para evitar las esquinas
                    index_x = max(min(index_x, screen_width - safe_margin), safe_margin)
                    index_y = max(min(index_y, screen_height - safe_margin), safe_margin)
                    pyautogui.moveTo(index_x, index_y)

                    if modo_arrastre:
                        pyautogui.mouseDown()  # Mantén el clic del ratón
                        print("Modo arrastre activado.")  # Mensaje de depuración

            else:
                if modo_arrastre:
                    pyautogui.mouseDown()  # Asegúrate de que el clic se mantiene incluso si no se detectan manos
                    print("Manteniendo clic en modo arrastre.")  # Mensaje de depuración

            cv2.imshow('Virtual Mouse', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
