"""
commands_v2.py  -  version 2 of the gesture commands.

It BUILDS ON commands.py (the original file is NOT changed).
From commands.py we re-use: get_features, next_number, speak, notify,
open_viewer, close_viewer, update_state, app_state and the settings.

What is new in v2:
  1. FEATURE SELECTION: the model uses only the 5 fingertips (10 numbers)
     instead of all 21 points (42 numbers).
  2. CUSTOM GESTURES: each gesture can be linked to any action
     (saved in settings.json). Example: victory -> open outlook.
  3. NEW ACTIONS: copy, paste, voice typing (Win+H), on-screen keyboard,
     open any app or website by typing its name.
  4. EMAIL: choose Gmail or Outlook in the settings.
"""
import ctypes
import json
import threading
import os
import subprocess
import time
import webbrowser
from urllib.parse import quote

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import commands as base                      # the original file, unchanged
from commands import (app_state, close_viewer, get_features, next_number,
                      notify, open_viewer, speak, update_state, LINES, OUT,
                      BASE, CONFIRM_SECONDS, EMAIL_BODY, AUTO_SEND_DELAY)

SETTINGS_FILE = os.path.join(BASE, "settings.json")

# ------------------------------------------------------------------
# 0) A BETTER FILE WINDOW (fixes "voice typing writes and deletes at the same time")
# ------------------------------------------------------------------
# The old window re-read the file every second and erased what you typed (or said).
# This one: (1) you can type or use voice typing in it, (2) every change is SAVED to the
# file at once, (3) it only reloads the file when the program changed it (the ok gesture),
# never while you are writing, (4) it takes the keyboard focus when it opens.
VIEWER_CODE_V2 = (
    "import os, sys, tkinter as tk\n"
    "path = sys.argv[1]\n"
    "root = tk.Tk()\n"
    "root.title(os.path.basename(path))\n"
    "box = tk.Text(root, width=45, height=8, font=('Arial', 14), wrap='word')\n"
    "box.pack(padx=10, pady=10)\n"
    "last = {'text': ''}\n"
    "def read():\n"
    "    try:\n"
    "        return open(path, encoding='utf-8', errors='replace').read()\n"
    "    except OSError:\n"
    "        return last['text']\n"
    "def load():\n"
    "    text = read()\n"
    "    box.delete('1.0', 'end')\n"
    "    box.insert('1.0', text)\n"
    "    last['text'] = text\n"
    "    box.edit_modified(False)\n"
    "def save(event=None):\n"
    "    if box.edit_modified():\n"
    "        text = box.get('1.0', 'end-1c')\n"
    "        with open(path, 'w', encoding='utf-8') as f:\n"
    "            f.write(text)\n"
    "        last['text'] = text\n"
    "        box.edit_modified(False)\n"
    "def refresh():\n"
    "    if read() != last['text'] and not box.edit_modified():\n"
    "        load()\n"
    "    root.after(1000, refresh)\n"
    "def focus():\n"
    "    root.attributes('-topmost', True)\n"
    "    root.lift(); root.focus_force(); box.focus_set()\n"
    "    root.after(300, lambda: root.attributes('-topmost', False))\n"
    "box.bind('<<Modified>>', save)\n"
    "load()\n"
    "box.mark_set('insert', 'end')\n"
    "refresh()\n"
    "root.after(200, focus)\n"
    "root.mainloop()\n"
)
base.VIEWER_CODE = VIEWER_CODE_V2     # open_viewer() in commands.py will now use the new window

# ------------------------------------------------------------------
# 1) FEATURE SELECTION
# ------------------------------------------------------------------
# Landmark numbers: 4 = thumb tip, 8 = index tip, 12 = middle tip,
#                   16 = ring tip, 20 = pinky tip.
# We tested this in the notebook: fingertips only gave 97.2% (all 42
# numbers gave 97.0%), so we use fewer numbers with the same accuracy.
# To go back to all points, write:  SELECTED_POINTS = None
SELECTED_POINTS = [4, 8, 12, 16, 20]


def selected_columns(all_columns):
    """Keep only the columns of the selected points (x4, y4, x8, y8 ...)."""
    if SELECTED_POINTS is None:
        return list(all_columns)
    wanted = []
    for p in SELECTED_POINTS:
        wanted += ["x" + str(p), "y" + str(p)]
    return wanted


# Extra data we recorded later (for example in a new room, with record_more_data.py).
# If a file in this list exists, it is added to gestures.csv when the model is trained.
EXTRA_CSVS = ["gestures_room2.csv"]


def load_data():
    """gestures.csv + any extra recorded file that exists."""
    data = pd.read_csv(os.path.join(BASE, "gestures.csv"))
    for name in EXTRA_CSVS:
        path = os.path.join(BASE, name)
        if os.path.exists(path):
            data = pd.concat([data, pd.read_csv(path)], ignore_index=True)
            print("added extra data:", name)
    return data


def make_model():
    """Train the Random Forest on the data using only the selected columns."""
    data = load_data()
    all_cols = [c for c in data.columns if c not in ["label", "session"]]
    cols = selected_columns(all_cols)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(data[cols], data["label"])
    return model, cols


def hand_to_row(hand, cols):
    """Hand landmarks -> one table row with the same selected columns.
    Step 1: compute all 42 numbers (centered on wrist and scaled, like in training).
    Step 2: keep only the selected ones."""
    all_numbers = get_features(hand)
    names = []
    for i in range(21):
        names += ["x" + str(i), "y" + str(i)]
    full = dict(zip(names, all_numbers))
    return pd.DataFrame([[full[c] for c in cols]], columns=cols)


# ------------------------------------------------------------------
# 2) SETTINGS (saved in settings.json, so they stay after closing)
# ------------------------------------------------------------------
# Every action has a short name. A gesture is linked to an action name.
# "target" is only used by open_app (for example: gmail, outlook, slack).
ACTION_LABELS = {
    "new_folder": "Create a new folder",
    "new_file": "Create a file and open it",
    "write_line": "Write the next line in the file",
    "close_window": "Close the file window",
    "say_yes": "Say Yes",
    "say_no": "Say No",
    "prepare_email": "Prepare an email (then confirm)",
    "copy": "Copy (Ctrl+C)",
    "paste": "Paste (Ctrl+V)",
    "voice_typing": "Voice typing (Win+H)",
    "voice_note": "Voice note: new file + start voice typing",
    "keyboard": "Open on-screen keyboard",
    "open_app": "Open an app or website (type its name)",
    "nothing": "Do nothing",
}

SETTINGS_VERSION = 3     # if settings.json has an older version, the new defaults are used

DEFAULT_SETTINGS = {
    "version": SETTINGS_VERSION,
    "gestures": {
        "open_palm": {"action": "new_folder", "target": ""},
        "victory": {"action": "new_file", "target": ""},
        "ok": {"action": "write_line", "target": ""},
        "fist": {"action": "close_window", "target": ""},
        "thumbs_up": {"action": "say_yes", "target": ""},
        "thumbs_down": {"action": "say_no", "target": ""},
        "call_me": {"action": "prepare_email", "target": ""},
        # two-hand gestures (found by rules in poses.py, not by the model)
        "two_open_hands": {"action": "keyboard", "target": ""},
        "two_fists": {"action": "voice_note", "target": ""},
    },
    "email_provider": "gmail",                 # "gmail" or "outlook"
    "email_to": base.DEFAULT_TO,
}


def load_settings():
    """Read settings.json. If it is missing or broken, use the defaults."""
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))   # a fresh copy
    try:
        with open(SETTINGS_FILE) as f:
            saved = json.load(f)
        if saved.get("version") == SETTINGS_VERSION:      # old files: use the new defaults
            settings["gestures"].update(saved.get("gestures", {}))
        for key in ("email_provider", "email_to"):
            if key in saved:
                settings[key] = saved[key]
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


SETTINGS = load_settings()


# ------------------------------------------------------------------
# 3) KEYBOARD HELPERS (Windows, ctypes, no installation)
# ------------------------------------------------------------------
KEYEVENTF_KEYUP = 0x0002
VK = {"ctrl": 0x11, "win": 0x5B, "c": 0x43, "v": 0x56, "h": 0x48}


def press_keys(*names):
    """Press keys together, for example press_keys("ctrl", "c")."""
    try:
        user32 = ctypes.windll.user32
    except AttributeError:          # not Windows
        return False
    codes = [VK[n] for n in names]
    for code in codes:              # hold all keys down ...
        user32.keybd_event(code, 0, 0, 0)
    for code in reversed(codes):    # ... then release them
        user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
    return True


def open_keyboard():
    """Open the Windows on-screen keyboard.
    We use 'cmd /c start osk' (not osk.exe directly), because Windows then finds the
    right osk.exe by itself, even with a 32-bit Python."""
    try:
        subprocess.Popen(["cmd", "/c", "start", "", "osk"],
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return "On-screen keyboard opened"
    except OSError as error:
        return "Could not open the on-screen keyboard: " + str(error)


def voice_typing():
    """Windows Voice Typing: click in a text box first, then speak.
    It uses Microsoft's own speech recognition (needs internet)."""
    if press_keys("win", "h"):
        return "Voice typing started: speak now (click a text box first)"
    return "Voice typing works on Windows only"


# ------------------------------------------------------------------
# 4) OPEN AN APP OR WEBSITE BY NAME
# ------------------------------------------------------------------
KNOWN = {
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.office.com/mail",
    "slack": "https://app.slack.com",
    "teams": "https://teams.microsoft.com",
    "whatsapp": "https://web.whatsapp.com",
    "youtube": "https://www.youtube.com",
    "calendar": "https://calendar.google.com",
    "drive": "https://drive.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "chrome": "chrome",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "explorer": "explorer",
    "paint": "mspaint",
}


def open_target(name):
    """Open a known name, a web link, or any Windows app name."""
    name = name.strip()
    if not name:
        return "No app name set: type one in the settings"
    key = name.lower().lstrip("\\")          # allow "\slack" too
    if key in KNOWN:
        target = KNOWN[key]
    elif key.startswith("http"):
        target = key
    elif "." in key and " " not in key:     # looks like a site, e.g. github.com
        target = "https://" + key
    else:
        target = key                        # try it as a Windows app name
    if target.startswith("http"):
        webbrowser.open(target)
        return "Opened " + key
    try:
        subprocess.Popen(["cmd", "/c", "start", "", target])
        return "Tried to open " + key
    except OSError:
        return "Could not open " + key


# ------------------------------------------------------------------
# 5) EMAIL (Gmail or Outlook in the browser, no password needed)
# ------------------------------------------------------------------
def email_draft_and_send(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        file_text = f.read()
    body = (EMAIL_BODY + "\n\n--- " + os.path.basename(path) + " ---\n" + file_text)
    to = SETTINGS["email_to"]
    if SETTINGS["email_provider"] == "outlook":
        url = ("https://outlook.office.com/mail/deeplink/compose?to=" + quote(to)
               + "&subject=" + quote("Call me now") + "&body=" + quote(body))
    else:
        url = ("https://mail.google.com/mail/?view=cm&fs=1&to=" + quote(to)
               + "&su=" + quote("Call me now") + "&body=" + quote(body))
    webbrowser.open(url)
    # wait for the page to load, then press Ctrl+Enter (= Send)
    cmd = ("Start-Sleep -Seconds " + str(AUTO_SEND_DELAY) + "; "
           "Add-Type -AssemblyName System.Windows.Forms; "
           "[System.Windows.Forms.SendKeys]::SendWait('^{ENTER}')")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd], creationflags=flags)
    except OSError:
        return "Could not press Send"
    return (SETTINGS["email_provider"].capitalize() + " opened, sending in "
            + str(AUTO_SEND_DELAY) + " s (keep that tab in front)")


# ------------------------------------------------------------------
# 6) THE ACTIONS (one small function for each action name)
# ------------------------------------------------------------------
def act_new_folder(target):
    number = next_number(OUT, "folder_")
    folder = os.path.join(OUT, "folder_" + str(number))
    os.makedirs(folder)
    app_state["folder"] = folder
    app_state["last_file"] = None
    try:
        os.startfile(folder)
    except (AttributeError, OSError):
        pass
    return "Created folder_" + str(number)


def make_folder_if_needed():
    """Make a folder if we do not have one yet (without opening Explorer)."""
    if app_state["folder"] is None:
        number = next_number(OUT, "folder_")
        folder = os.path.join(OUT, "folder_" + str(number))
        os.makedirs(folder)
        app_state["folder"] = folder


def make_new_file():
    number = next_number(app_state["folder"], "quick_file_", ".txt")
    path = os.path.join(app_state["folder"], "quick_file_" + str(number) + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("")                      # empty: ready for voice typing
    app_state["last_file"] = path
    return number, path


def act_new_file(target):
    if app_state["folder"] is None:
        return "No folder yet: make a folder first"
    number, path = make_new_file()
    with open(path, "w", encoding="utf-8") as f:
        f.write("Quick file " + str(number) + "\nCreated at " + time.strftime("%H:%M:%S"))
    if open_viewer(path):
        return "Created and opened quick_file_" + str(number)
    try:
        os.startfile(path)
        return "Created quick_file_" + str(number) + " (opened in Notepad)"
    except (AttributeError, OSError):
        return "Created quick_file_" + str(number)


def act_voice_note(target):
    """ONE gesture = folder (if needed) + new empty file + open it + start voice typing.
    The file window can be edited and saves everything you say."""
    make_folder_if_needed()
    number, path = make_new_file()
    if not open_viewer(path):
        return "Could not open the file window"
    threading.Timer(1.5, voice_typing).start()      # wait for the window to take the focus
    return "Voice note quick_file_" + str(number) + ": speak now (Win+H again to stop)"


def act_write_line(target):
    if app_state["last_file"] is None:
        return "No file yet: make a file first"
    line = LINES[app_state["line_index"] % len(LINES)]
    app_state["line_index"] += 1
    with open(app_state["last_file"], "a", encoding="utf-8") as f:
        f.write("\n" + line)
    proc = app_state["viewer"]
    if proc is None or proc.poll() is not None:
        open_viewer(app_state["last_file"])
    return "Wrote: " + line[:30] + "..."


def act_close_window(target):
    return "Closed the window" if close_viewer() else "Nothing to close"


def act_say(phrase):
    speak(phrase)
    notify(phrase, 2)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "messages.txt"), "a") as f:
        f.write(time.strftime("%H:%M:%S") + "  " + phrase + "\n")
    return phrase


def act_prepare_email(target):
    if app_state["last_file"] is None:
        return "No file yet: make a file first"
    name = os.path.basename(app_state["last_file"])
    app_state["pending_until"] = time.time() + CONFIRM_SECONDS
    notify("Send email with " + name + "?\nVICTORY = SEND     FIST = CANCEL", CONFIRM_SECONDS)
    return "Email with " + name + "? victory = SEND, fist = cancel"


def act_copy(target):
    return "Copied (Ctrl+C)" if press_keys("ctrl", "c") else "Windows only"


def act_paste(target):
    return "Pasted (Ctrl+V)" if press_keys("ctrl", "v") else "Windows only"


ACTIONS = {
    "new_folder": act_new_folder,
    "new_file": act_new_file,
    "voice_note": act_voice_note,
    "write_line": act_write_line,
    "close_window": act_close_window,
    "say_yes": lambda t: act_say("Yes"),
    "say_no": lambda t: act_say("No"),
    "prepare_email": act_prepare_email,
    "copy": act_copy,
    "paste": act_paste,
    "voice_typing": lambda t: voice_typing(),
    "keyboard": lambda t: open_keyboard(),
    "open_app": lambda t: open_target(t),
    "nothing": lambda t: "",
}


def run_command(gesture):
    """Run the action linked to this gesture (from settings.json)."""
    os.makedirs(OUT, exist_ok=True)

    # A waiting email: victory = SEND, fist = CANCEL (always, whatever the settings)
    if time.time() < app_state["pending_until"]:
        if gesture == "victory":
            app_state["pending_until"] = 0.0
            speak("Sent")
            return email_draft_and_send(app_state["last_file"])
        if gesture == "fist":
            app_state["pending_until"] = 0.0
            notify("Email cancelled", 3)
            return "Email cancelled"

    link = SETTINGS["gestures"].get(gesture)
    if link is None:
        return ""
    function = ACTIONS.get(link["action"])
    if function is None:
        return "Unknown action: " + link["action"]
    return function(link.get("target", ""))
