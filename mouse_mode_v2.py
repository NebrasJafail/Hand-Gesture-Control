"""
mouse_mode_v2.py  -  version 2 of mouse mode (the original mouse_mode.py is NOT changed).

New in v2:
  - ON / OFF posture: hold a FIST for 1.5 s = mouse PAUSED,
                      hold an OPEN PALM for 1.5 s = mouse ACTIVE again.
  - Smoother cursor: slow hand = very smooth, fast hand = quick.
  - Click happens when you OPEN the pinch (so dragging is possible).
  - Double click: pinch twice quickly (Windows turns two quick clicks into one double click).
  - Drag: keep the pinch closed for 0.6 s, move the hand, open the pinch to drop.
  - Right click: HORNS pose (index + pinky up), see poses.py. (thumb + middle is OFF)
  - No scroll (it still does not work).
Mouse mode is still an early test.
"""
import ctypes
import math
import time

# ---------- settings (change these to tune it) ----------
MARGIN = 0.2        # ignore the edges of the camera, so you can reach the screen corners
SMOOTH_MIN = 0.08   # slow hand: very smooth
SMOOTH_MAX = 0.5    # fast hand: follows quickly
PINCH_ON = 0.25     # pinch ratio below this = fingers touching
PINCH_OFF = 0.40    # pinch ratio above this = fingers open again
DRAG_HOLD = 0.6     # seconds of holding a pinch before it becomes a drag
SWITCH_HOLD = 1.5   # seconds of holding fist / open palm to switch the mouse OFF / ON
                    # (only used if app_v2 does not choose the mode by hand pose)
RIGHT_CLICK_THUMB_MIDDLE = False   # old right click (thumb + middle). OFF: the new one is the HORNS pose
RIGHT_CLICK_WAIT = 1.0             # seconds between two right clicks

try:
    user32 = ctypes.windll.user32            # Windows only, no installation needed
except AttributeError:                       # (so the file can still be tested elsewhere)
    class _Fake:
        def GetSystemMetrics(self, i):
            return 1920 if i == 0 else 1080

        def SetCursorPos(self, x, y):
            pass

        def mouse_event(self, *args):
            pass
    user32 = _Fake()

SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)
LEFT_DOWN, LEFT_UP = 0x0002, 0x0004
RIGHT_DOWN, RIGHT_UP = 0x0008, 0x0010


def new_mouse_state():
    return {
        "x": None, "y": None,
        "active": True,          # ON / OFF posture
        "hold_label": None, "hold_start": 0.0,
        "pinched": False, "pinch_start": 0.0, "dragging": False,
        "right_pinched": False, "last_right_click": 0.0,
    }


def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def ratio(hand, a, b):
    """Distance between points a and b, divided by hand size (wrist 0 to middle knuckle 9)."""
    return distance(hand[a], hand[b]) / distance(hand[0], hand[9])


def left_click():
    user32.mouse_event(LEFT_DOWN, 0, 0, 0, 0)
    user32.mouse_event(LEFT_UP, 0, 0, 0, 0)


def right_click():
    user32.mouse_event(RIGHT_DOWN, 0, 0, 0, 0)
    user32.mouse_event(RIGHT_UP, 0, 0, 0, 0)


def move_cursor(hand, ms):
    """Index tip -> cursor, with speed-based smoothing."""
    tip = hand[8]
    x = (1 - tip.x - MARGIN) / (1 - 2 * MARGIN)   # 1 - x because the picture is mirrored
    y = (tip.y - MARGIN) / (1 - 2 * MARGIN)
    x = min(max(x, 0.0), 1.0)
    y = min(max(y, 0.0), 1.0)
    target_x, target_y = x * (SCREEN_W - 1), y * (SCREEN_H - 1)
    if ms["x"] is None:
        ms["x"], ms["y"] = target_x, target_y
    else:
        gap = math.hypot(target_x - ms["x"], target_y - ms["y"])      # how far the target is
        smooth = min(SMOOTH_MAX, SMOOTH_MIN + gap / (SCREEN_W * 0.25))  # far = faster
        ms["x"] += (target_x - ms["x"]) * smooth
        ms["y"] += (target_y - ms["y"]) * smooth
    user32.SetCursorPos(int(ms["x"]), int(ms["y"]))


def release_everything(ms):
    """Safety: never leave the mouse button held down."""
    if ms["dragging"]:
        user32.mouse_event(LEFT_UP, 0, 0, 0, 0)
    ms["dragging"] = False
    ms["pinched"] = False
    ms["right_pinched"] = False


def switch_posture(label, ms, now):
    """Hold fist = OFF, hold open palm = ON. Returns True if the state changed."""
    wanted = {"fist": False, "open_palm": True}.get(label)
    if wanted is None or wanted == ms["active"]:
        ms["hold_label"] = None
        return False
    if ms["hold_label"] != label:
        ms["hold_label"], ms["hold_start"] = label, now
        return False
    if now - ms["hold_start"] >= SWITCH_HOLD:
        ms["active"] = wanted
        ms["hold_label"] = None
        if not wanted:
            release_everything(ms)
        return True
    return False


def pose_right_click(ms, now=None):
    """Called while the HORNS pose (index + pinky up) is held. One right click, then wait a bit."""
    now = time.time() if now is None else now
    if now - ms["last_right_click"] < RIGHT_CLICK_WAIT:
        return False
    ms["last_right_click"] = now
    right_click()
    return True


def mouse_step(hand, ms, label=None, now=None):
    """Call once per frame. hand = 21 landmarks, label = gesture the model sees.
    Returns a short status text: ACTIVE / PAUSED / DRAGGING."""
    now = time.time() if now is None else now
    switch_posture(label, ms, now)
    if not ms["active"]:
        return "PAUSED (hold open palm to start)"

    pinch = ratio(hand, 4, 8)         # thumb + index  = left click / drag
    right = ratio(hand, 4, 12)        # thumb + middle = right click

    # 1) move the cursor (frozen during a short pinch, so the click does not shake it)
    if not ms["pinched"] or ms["dragging"]:
        move_cursor(hand, ms)

    # 2) left click / drag
    if not ms["pinched"] and pinch < PINCH_ON:
        ms["pinched"], ms["pinch_start"] = True, now
    elif ms["pinched"]:
        if not ms["dragging"] and pinch < PINCH_ON and now - ms["pinch_start"] >= DRAG_HOLD:
            ms["dragging"] = True
            user32.mouse_event(LEFT_DOWN, 0, 0, 0, 0)       # pick up
        if pinch > PINCH_OFF:                               # fingers opened
            if ms["dragging"]:
                user32.mouse_event(LEFT_UP, 0, 0, 0, 0)     # drop
                ms["dragging"] = False
            else:
                left_click()      # two quick clicks = double click (done by Windows)
            ms["pinched"] = False

    # 3) old right click (thumb + middle). It is OFF by default (see RIGHT_CLICK_THUMB_MIDDLE),
    #    because in the POINT pose the thumb often touches the bent middle finger by accident.
    if RIGHT_CLICK_THUMB_MIDDLE and not ms["pinched"]:
        if not ms["right_pinched"] and right < PINCH_ON:
            ms["right_pinched"] = True
            right_click()
        elif ms["right_pinched"] and right > PINCH_OFF:
            ms["right_pinched"] = False

    return "DRAGGING" if ms["dragging"] else "ACTIVE"
