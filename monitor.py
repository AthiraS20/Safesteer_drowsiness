import cv2
import mediapipe as mp
import time
import threading
import pygame
import sqlite3
import argparse
import os
import urllib.request
from pathlib import Path

from audio_alerts import (
    trigger_mayday_alert,
    trigger_drowsy_beep,
    trigger_phone_warning,
    trigger_sleepy_reminder,
    trigger_safe_chime,
    trigger_system_boot,
    trigger_emergency_protocol,
    voice_alert,
    play_sound,
)

from db import DB_PATH, init_db

# Ensure tables and schema are initialized
init_db()

def log_incident(user_id, incident_type):
    """Store an incident into DB for given user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO incidents (user_id, type) VALUES (?, ?)", (user_id, incident_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB Error] Failed to log incident '{incident_type}': {e}")

# === Shared variables for status messages ===
status_text = ""
last_status_time = 0
status_duration = 1.5  # seconds
rescue_call_active = False

# === Horn and simulated rescue call ===
def play_horn_and_call(user_id):
    global status_text, last_status_time, rescue_call_active

    rescue_call_active = True
    status_text = "Calling the rescue team..."
    last_status_time = time.time()

    trigger_emergency_protocol(user_id, log_incident)
    time.sleep(3)
    rescue_call_active = False

# === EAR calculation ===
def calculate_ear(eye):
    A = ((eye[1][0] - eye[5][0])**2 + (eye[1][1] - eye[5][1])**2)**0.5
    B = ((eye[2][0] - eye[4][0])**2 + (eye[2][1] - eye[4][1])**2)**0.5
    C = ((eye[0][0] - eye[3][0])**2 + (eye[0][1] - eye[3][1])**2)**0.5
    return (A + B) / (2.0 * C)

# === MediaPipe Setup ===
if hasattr(mp, "solutions"):
    mp_solutions = getattr(mp, "solutions")
    mp_face = mp_solutions.face_mesh
    mp_hands = mp_solutions.hands
    face_mesh = mp_face.FaceMesh(refine_landmarks=True)
    hands = mp_hands.Hands(max_num_hands=1)
else:
    from mediapipe.tasks.python import vision, BaseOptions

    BASE_DIR = Path(__file__).resolve().parent
    MODELS_DIR = BASE_DIR / "models"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    face_model_path = str(MODELS_DIR / "face_landmarker.task")
    hand_model_path = str(MODELS_DIR / "hand_landmarker.task")

    def _ensure_model(path, url):
        if not os.path.exists(path):
            print(f"Downloading {Path(path).name}...")
            urllib.request.urlretrieve(url, path)

    _ensure_model(
        face_model_path,
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    )
    _ensure_model(
        hand_model_path,
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    )

    class _LandmarkWrapper:
        def __init__(self, landmarks):
            self.landmark = landmarks

    class _TasksFaceMesh:
        def __init__(self, model_path):
            options = vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=model_path),
                running_mode=vision.RunningMode.IMAGE,
                num_faces=1
            )
            self.detector = vision.FaceLandmarker.create_from_options(options)

        def process(self, rgb_frame):
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            res = self.detector.detect(mp_img)
            class Output:
                pass
            out = Output()
            out.multi_face_landmarks = [_LandmarkWrapper(lms) for lms in res.face_landmarks] if res.face_landmarks else None
            return out

    class _TasksHands:
        def __init__(self, model_path):
            options = vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=model_path),
                running_mode=vision.RunningMode.IMAGE,
                num_hands=1
            )
            self.detector = vision.HandLandmarker.create_from_options(options)

        def process(self, rgb_frame):
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            res = self.detector.detect(mp_img)
            class Output:
                pass
            out = Output()
            out.multi_hand_landmarks = [_LandmarkWrapper(lms) for lms in res.hand_landmarks] if res.hand_landmarks else None
            return out

    face_mesh = _TasksFaceMesh(face_model_path)
    hands = _TasksHands(hand_model_path)

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
EAR_THRESHOLD = 0.18
EYE_CLOSED_FRAMES = 18  # Rapid detection (~0.7s) on each eye closure
PHONE_USAGE_FRAMES = 120  # ~4-5 seconds at 25fps

# === Tracking Variables ===
closed_frames = 0
consec_alerts = 0
nonconsec_alerts = 0  # <-- for sleepy reminder
incident_triggered = False
horn_active = False
phone_frames = 0
voice_alert_given = False

# === Get user_id from CLI ===
parser = argparse.ArgumentParser()
parser.add_argument("--user_id", required=True, help="User ID from Flask session")
args = parser.parse_args()
USER_ID = args.user_id

# === Camera ===
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Warning: Camera 0 could not be opened. Please verify camera access.")

# Boot chime and robotic voice announcement
threading.Thread(target=trigger_system_boot, daemon=True).start()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera feed ended or unavailable.")
        break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_result = face_mesh.process(rgb)
    hand_result = hands.process(rgb)

    # === Phone Usage Detection ===
    if face_result.multi_face_landmarks and hand_result.multi_hand_landmarks:
        face = face_result.multi_face_landmarks[0].landmark
        hand = hand_result.multi_hand_landmarks[0].landmark

        nose = face[1]
        tx, ty = int(hand[4].x * w), int(hand[4].y * h)  # Thumb
        ix, iy = int(hand[8].x * w), int(hand[8].y * h)  # Index
        nx, ny = int(nose.x * w), int(nose.y * h)        # Nose

        dist_thumb_nose = ((tx - nx) ** 2 + (ty - ny) ** 2) ** 0.5
        dist_index_nose = ((ix - nx) ** 2 + (iy - ny) ** 2) ** 0.5
        dist_thumb_index = ((tx - ix) ** 2 + (ty - iy) ** 2) ** 0.5

        if ((dist_thumb_nose < 100 or dist_index_nose < 100) and dist_thumb_index > 30):
            phone_frames += 1
        else:
            phone_frames = 0
    else:
        phone_frames = 0

    if phone_frames > PHONE_USAGE_FRAMES:
        trigger_phone_warning()
        phone_frames = 0
        status_text = "Phone Usage Detected"
        last_status_time = time.time()
        log_incident(USER_ID, "Phone Usage")

    # === Eye Monitoring ===
    if face_result.multi_face_landmarks:
        lm = face_result.multi_face_landmarks[0].landmark

        def get_eye_points(indices):
            return [(int(lm[i].x * w), int(lm[i].y * h)) for i in indices]

        left_eye = get_eye_points(LEFT_EYE)
        right_eye = get_eye_points(RIGHT_EYE)
        ear = (calculate_ear(left_eye) + calculate_ear(right_eye)) / 2.0

        cv2.putText(frame, f"EAR: {ear:.2f}", (30, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        if ear < EAR_THRESHOLD:
            closed_frames += 1
            if closed_frames > EYE_CLOSED_FRAMES and not horn_active:
                if trigger_mayday_alert(cooldown=2.5):
                    consec_alerts += 1
                    status_text = "MAYDAY! YOU ARE IN DANGER!"
                    last_status_time = time.time()
                    if not incident_triggered:
                        log_incident(USER_ID, "Drowsiness (Mayday)")
        else:
            if closed_frames > EYE_CLOSED_FRAMES:  
                # eye reopened after drowsy episode
                trigger_safe_chime()
                nonconsec_alerts += 1
                if nonconsec_alerts >= 3 and not voice_alert_given:
                    trigger_sleepy_reminder()
                    voice_alert_given = True
                    nonconsec_alerts = 0

            closed_frames = 0
            consec_alerts = 0
            horn_active = False
            incident_triggered = False

    # === Incident detection after 3 consecutive alerts ===
    if consec_alerts >= 3 and not incident_triggered:
        horn_active = True
        incident_triggered = True
        consec_alerts = 0
        nonconsec_alerts = 0
        voice_alert_given = False
        status_text = "Driver Unresponsive – Incident Detected"
        last_status_time = time.time()
        threading.Thread(target=play_horn_and_call, args=(USER_ID,), daemon=True).start()

    # === Display message if active or within 1.5 seconds ===
    if rescue_call_active or (time.time() - last_status_time < status_duration):
        cv2.putText(frame, status_text, (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

    cv2.imshow("Driver Monitoring System", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        pygame.mixer.stop()
        pygame.mixer.music.stop()
        break

cap.release()
cv2.destroyAllWindows()
