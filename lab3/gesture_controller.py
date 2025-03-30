import cv2
import mediapipe as mp
import threading
import time

class GestureController:
    def __init__(self, callback):
        # callback(gesture_type) – np. "pinch"
        self.callback = callback
        self.running = False
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1)
        self.mp_draw = mp.solutions.drawing_utils

    def start(self):
        self.running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def stop(self):
        self.running = False

    def _run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("GestureController: Nie można otworzyć kamery.")
            return
        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                    index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    # Wykrywanie gestu "pinch"
                    pinch_dist = ((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2) ** 0.5
                    if pinch_dist < 0.05:
                        self.callback("pinch")
                        time.sleep(1)
                    else:
                        # Oblicz dystanse z nadgarstka do końcówek palców: index, middle, ring, pinky
                        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
                        index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                        middle_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                        ring_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
                        pinky_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.PINKY_FINGER_TIP]
                        def distance(a, b):
                            return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5
                        index_d = distance(wrist, index_tip)
                        middle_d = distance(wrist, middle_tip)
                        ring_d = distance(wrist, ring_tip)
                        pinky_d = distance(wrist, pinky_tip)
                        # Jeżeli wszystkie dystanse są niskie, przyjmujemy, że ręka jest zaciśnięta (fist)
                        if index_d < 0.2 and middle_d < 0.2 and ring_d < 0.2 and pinky_d < 0.2:
                            self.callback("fist")
                            time.sleep(1)
                        # Jeżeli wszystkie dystanse są wysokie, przyjmujemy, że ręka jest otwarta (open)
                        elif index_d > 0.3 and middle_d > 0.3 and ring_d > 0.3 and pinky_d > 0.3:
                            self.callback("open")
                            time.sleep(1)
            cv2.waitKey(1)
        cap.release()
        cv2.destroyAllWindows()
