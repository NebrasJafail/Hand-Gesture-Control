import os
import subprocess
import sys
import time
import webbrowser
from urllib.parse import quote

import cv2
import mediapipe as mp
import pandas as pd
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from sklearn.ensemble import RandomForestClassifier

# ---------- settings ----------
CONFIDENCE = 0.8   # model must be at least this sure
HOLD_FRAMES = 8    # the same gesture must be held for this many frames in a row
COOLDOWN = 3.0     # seconds to wait after a command before the next one

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "demo_output")

# Control gestures (act on the computer)
CONTROL = {
    "open_palm": "Create quick file",
    "victory": "Open last file in a window",
    "fist": "Close that window",
}

# Talk gestures (say a ready phrase out loud)
PHRASES = {
    "thumbs_up": "Yes",
    "thumbs_down": "No",
}

# Email settings (no password needed: we use Gmail in your browser)
DEFAULT_TO = "nebrasjafail@gmail.com"   # who receives the email: change it here if you want
EMAIL_TO = DEFAULT_TO
CONFIRM_SECONDS = 20   # time you have to confirm before the email is cancelled

# Ready lines that the ok gesture writes into the last file, one per gesture
LINES = [
    "Hello, this file was written by hand gestures.",
    "I can control the computer without a keyboard.",
    "This is a communication tool for people who cannot speak.",
]

EMAIL_BODY = ("Please call me now. I am using my laptop remotely, "
              "and I cannot use it or type on the keyboard right now.")

# What we have opened (so we only ever close our own window)
app_state = {"last_file": None, "viewer": None, "pending_until": 0.0, "line_index": 0, "folder": None}


# ---------- hand features ----------
def get_features(landmarks):
    wrist_x, wrist_y = landmarks[0].x, landmarks[0].y
    coords = [(p.x - wrist_x, p.y - wrist_y) for p in landmarks]
    scale = max(max(abs(x), abs(y)) for x, y in coords)
    features = []
    for x, y in coords:
        features.append(x / scale)
        features.append(y / scale)
    return features


# ---------- commands ----------
def next_number(directory, prefix, suffix=""):
    """Highest existing number for names like prefix + N + suffix, plus 1."""
    highest = 0
    if os.path.isdir(directory):
        for name in os.listdir(directory):
            if name.startswith(prefix) and name.endswith(suffix):
                number = name[len(prefix):len(name) - len(suffix)]
                if number.isdigit():
                    highest = max(highest, int(number))
    return highest + 1


def speak(text):
    """Read text aloud with the built-in Windows voice (no install needed)."""
    cmd = ("Add-Type -AssemblyName System.Speech; "
           "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('" + text + "')")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd], creationflags=flags)
    except OSError:
        pass


VIEWER_CODE = (
    "import os, sys, tkinter as tk\n"
    "path = sys.argv[1]\n"
    "root = tk.Tk()\n"
    "root.title(os.path.basename(path))\n"
    "box = tk.Text(root, width=45, height=8, font=('Arial', 14))\n"
    "box.pack(padx=10, pady=10)\n"
    "def refresh():\n"
    "    box.delete('1.0', 'end')\n"
    "    box.insert('1.0', open(path).read())\n"
    "    root.after(1000, refresh)\n"
    "refresh()\n"
    "root.mainloop()\n"
)


NOTE_CODE = (
    "import sys, tkinter as tk\n"
    "root = tk.Tk()\n"
    "root.title('Gesture Control')\n"
    "root.attributes('-topmost', True)\n"
    "tk.Label(root, text=sys.argv[1], font=('Arial', 28), padx=40, pady=30).pack()\n"
    "root.after(int(float(sys.argv[2]) * 1000), root.destroy)\n"
    "root.mainloop()\n"
)


def notify(text, seconds=3):
    """Show a big message window in front of the user for a few seconds."""
    try:
        subprocess.Popen([sys.executable, "-c", NOTE_CODE, text, str(seconds)])
    except OSError:
        pass


def open_viewer(path):
    """Open a small window showing the file. Returns False if the window failed to start."""
    close_viewer()
    proc = subprocess.Popen([sys.executable, "-c", VIEWER_CODE, path])
    time.sleep(0.6)
    if proc.poll() is not None:   # it already exited, so it did not start
        app_state["viewer"] = None
        return False
    app_state["viewer"] = proc
    return True


def close_viewer():
    proc = app_state["viewer"]
    if proc is not None and proc.poll() is None:
        proc.terminate()
        app_state["viewer"] = None
        return True
    return False


AUTO_SEND_DELAY = 8   # seconds to let Gmail load before pressing Ctrl+Enter


def gmail_draft_and_send(path):
    """No app password: open a ready Gmail draft, then press Ctrl+Enter to send it."""
    with open(path) as f:
        file_text = f.read()
    name = os.path.basename(path)
    body = EMAIL_BODY + "\n\n--- " + name + " ---\n" + file_text
    url = ("https://mail.google.com/mail/?view=cm&fs=1&to=" + quote(EMAIL_TO)
           + "&su=" + quote("Call me now") + "&body=" + quote(body))
    webbrowser.open(url)
    cmd = ("Start-Sleep -Seconds " + str(AUTO_SEND_DELAY) + "; "
           "Add-Type -AssemblyName System.Windows.Forms; "
           "[System.Windows.Forms.SendKeys]::SendWait('^{ENTER}')")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd], creationflags=flags)
    except OSError:
        return "Could not press Send"
    return "Gmail opened, sending in " + str(AUTO_SEND_DELAY) + " seconds (keep the Gmail tab in front)"


def run_command(gesture):
    os.makedirs(OUT, exist_ok=True)

    # Last step: confirm (victory) or cancel (fist) a waiting email
    if time.time() < app_state["pending_until"]:
        if gesture == "victory":          # victory = SEND
            app_state["pending_until"] = 0.0
            speak("Sent")
            # no popup here: it would take the keyboard focus away from Gmail
            result = gmail_draft_and_send(app_state["last_file"])
            return result
        if gesture == "fist":             # fist = CANCEL
            app_state["pending_until"] = 0.0
            notify("Email cancelled", 3)
            return "Email cancelled"

    if gesture == "open_palm":
        number = next_number(OUT, "folder_")
        folder = os.path.join(OUT, "folder_" + str(number))
        os.makedirs(folder)
        app_state["folder"] = folder
        app_state["last_file"] = None
        print("Created folder:", folder)
        try:
            os.startfile(folder)   # shows the new folder in Explorer
        except (AttributeError, OSError):
            pass
        return "Created folder_" + str(number)

    if gesture == "victory":
        if app_state["folder"] is None:
            return "No folder yet: show an open palm first"
        number = next_number(app_state["folder"], "quick_file_", ".txt")
        path = os.path.join(app_state["folder"], "quick_file_" + str(number) + ".txt")
        with open(path, "w") as f:
            f.write("Quick file " + str(number) + "\nCreated at " + time.strftime("%H:%M:%S"))
        app_state["last_file"] = path
        print("Created file:", path)
        if open_viewer(path):
            return "Created and opened quick_file_" + str(number)
        try:
            os.startfile(path)   # Notepad fallback
            return "Created quick_file_" + str(number) + " (opened in Notepad)"
        except (AttributeError, OSError):
            return "Created quick_file_" + str(number)

    if gesture == "fist":
        if close_viewer():
            return "Closed the window"
        return "Nothing to close"

    if gesture == "ok":
        if app_state["last_file"] is None:
            return "No file yet: show a victory sign first"
        line = LINES[app_state["line_index"] % len(LINES)]
        app_state["line_index"] += 1
        with open(app_state["last_file"], "a") as f:
            f.write("\n" + line)
        print("Wrote a line into:", app_state["last_file"])
        proc = app_state["viewer"]
        if proc is None or proc.poll() is not None:
            open_viewer(app_state["last_file"])
        return "Wrote: " + line[:30] + "..."

    if gesture == "call_me":
        if app_state["last_file"] is None:
            return "No file yet: show a victory sign first"
        name = os.path.basename(app_state["last_file"])
        app_state["pending_until"] = time.time() + CONFIRM_SECONDS
        notify("Send email with " + name + "?\nVICTORY = SEND     FIST = CANCEL", CONFIRM_SECONDS)
        return "Email with " + name + "? victory = SEND, fist = cancel"

    if gesture in PHRASES:
        phrase = PHRASES[gesture]
        speak(phrase)
        notify(phrase, 2)
        with open(os.path.join(OUT, "messages.txt"), "a") as f:
            f.write(time.strftime("%H:%M:%S") + "  " + phrase + "\n")
        return phrase

    return ""


# ---------- avoid accidental triggers ----------
def update_state(state, label, conf, now):
    """Return a gesture only if it was held long enough, with high confidence.
    After a command runs, the same gesture will not run again until you change
    to another gesture (or take your hand away)."""
    if label != state.get("locked"):
        state["locked"] = None          # a different gesture (or no hand) unlocks

    if label is not None and conf >= CONFIDENCE and state.get("locked") is None:
        if label == state["label"]:
            state["count"] += 1
        else:
            state["label"] = label
            state["count"] = 1
    else:
        state["label"] = None
        state["count"] = 0

    if state["count"] >= HOLD_FRAMES and now - state["last_time"] > COOLDOWN:
        fired = state["label"]
        state["count"] = 0
        state["last_time"] = now
        state["locked"] = fired
        return fired
    return None


# ---------- live camera loop ----------
def main():
    # 0. make the output folder and show where it is
    os.makedirs(OUT, exist_ok=True)
    print("Files are saved in this folder:", OUT)
    try:
        os.startfile(OUT)   # opens the folder in Explorer (Windows)
    except (AttributeError, OSError):
        pass

    # 1. train the gesture model from our recorded data
    data = pd.read_csv(os.path.join(BASE, "gestures.csv"))
    feature_cols = [c for c in data.columns if c not in ["label", "session"]]
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(data[feature_cols], data["label"])
    print("model trained on", len(data), "samples:", list(model.classes_))

    # 2. hand detector
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(
            model_asset_path=os.path.join(BASE, "hand_landmarker.task")
        ),
        num_hands=1,
    )
    detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    state = {"label": None, "count": 0, "last_time": 0.0}
    message = "Show a gesture"

    print("Running. Press q in the camera window to quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))

        show = cv2.flip(frame, 1)
        label, conf = None, 0.0
        if len(result.hand_landmarks) == 1:
            hand = result.hand_landmarks[0]
            for p in hand:
                cv2.circle(show, (int((1 - p.x) * w), int(p.y * h)), 4, (0, 255, 0), -1)
            row = pd.DataFrame([get_features(hand)], columns=feature_cols)
            probs = model.predict_proba(row)[0]
            best = probs.argmax()
            label, conf = model.classes_[best], probs[best]

        triggered = update_state(state, label, conf, time.time())
        if triggered is not None:
            message = triggered + ": " + run_command(triggered)

        if label is None:
            info = "No hand"
        else:
            info = label + " " + str(int(conf * 100)) + "%"
        cv2.putText(show, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(show, message, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow("Gesture Control (press q to quit)", show)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    close_viewer()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
