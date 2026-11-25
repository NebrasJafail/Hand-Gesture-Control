"""
web_core.py  -  the recognition part of the project, without any Streamlit code.
Used by web_demo.py (the live web demo). It does the same steps as the full app:
  photo -> MediaPipe (21 points) -> 42 numbers -> 5 fingertips (10 numbers) -> Random Forest
"""
import os

import cv2
import mediapipe as mp
import pandas as pd
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from sklearn.ensemble import RandomForestClassifier

import poses

BASE = os.path.dirname(os.path.abspath(__file__))
POINTS = [4, 8, 12, 16, 20]          # the 5 fingertips (feature selection result)

# What each gesture does in the FULL app (it runs on the user's own computer)
FULL_APP_ACTION = {
    "open_palm": "Create a new folder",
    "victory": "Create a new file and open it (or SEND the email if one is waiting)",
    "ok": "Write the next line in the file",
    "fist": "Close the file window (or CANCEL the email)",
    "thumbs_up": "Say 'Yes' out loud",
    "thumbs_down": "Say 'No' out loud",
    "call_me": "Prepare an email 'Call me now' (confirm with victory)",
}
SHAPE_ACTION = {
    "POINT": "Mouse mode: the index finger moves the cursor, a pinch clicks",
    "HORNS": "Right click",
    "TWO": "Scroll (move the hand up or down)",
    "THREE": "Volume (turn the hand)",
}


def get_features(landmarks):
    """Same as the full app: subtract the wrist, divide by the biggest number (42 numbers)."""
    wrist_x, wrist_y = landmarks[0].x, landmarks[0].y
    coords = [(p.x - wrist_x, p.y - wrist_y) for p in landmarks]
    scale = max(max(abs(x), abs(y)) for x, y in coords)
    features = []
    for x, y in coords:
        features.append(x / scale)
        features.append(y / scale)
    return features


def selected_columns():
    cols = []
    for p in POINTS:
        cols += ["x" + str(p), "y" + str(p)]
    return cols


def train_model():
    data = pd.read_csv(os.path.join(BASE, "gestures.csv"))
    extra = os.path.join(BASE, "gestures_room2.csv")
    if os.path.exists(extra):
        data = pd.concat([data, pd.read_csv(extra)], ignore_index=True)
    cols = selected_columns()
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(data[cols], data["label"])
    return model, cols


def make_detector():
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(
            model_asset_path=os.path.join(BASE, "hand_landmarker.task")),
        num_hands=1,
    )
    return vision.HandLandmarker.create_from_options(options)


def analyze(image_bgr, model, cols, detector):
    """Returns a dict: found, label, confidence, shape, ranking (list), picture (RGB)."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    out = {"found": False, "picture": rgb}
    if len(result.hand_landmarks) != 1:
        return out
    hand = result.hand_landmarks[0]
    h, w = rgb.shape[:2]
    picture = rgb.copy()
    for p in hand:
        cv2.circle(picture, (int(p.x * w), int(p.y * h)), 5, (0, 255, 0), -1)
    names = []
    for i in range(21):
        names += ["x" + str(i), "y" + str(i)]
    full = dict(zip(names, get_features(hand)))
    row = pd.DataFrame([[full[c] for c in cols]], columns=cols)
    probs = model.predict_proba(row)[0]
    order = probs.argsort()[::-1]
    out.update({
        "found": True,
        "picture": picture,
        "label": model.classes_[order[0]],
        "confidence": float(probs[order[0]]),
        "ranking": [(model.classes_[i], float(probs[i])) for i in order[:3]],
        "shape": poses.pose_name(hand),
    })
    return out
