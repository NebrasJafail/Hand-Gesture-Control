"""
zoom_mode.py  -  ZOOM with two open hands, like pinch-to-zoom on a phone.

  two open hands move APART    = zoom in
  two open hands move TOGETHER = zoom out
  two open hands held STILL    = (the keyboard command, see app_v2.py)

How it works:
  1) every frame we measure the distance between the two wrists
  2) we divide it by the hand size, so it works near or far from the camera
  3) every time the distance changes by one "step" we send ONE zoom click:
     Ctrl + mouse wheel (it zooms a browser, a map, Word, photos ...)
If it zooms the wrong way, change SIGN to -1. If it is too fast or slow, change STEP.

"last_move" = the last time the hands moved. app_v2.py opens the keyboard
only when the hands were still for KEYBOARD_STILL seconds, so zooming does not open it.
"""
import ctypes
import math
import time

STEP = 0.25        # change of the distance between the hands (in hand sizes) for one zoom click
SIGN = 1           # 1 = hands apart zoom IN. -1 = the opposite
STILL_TOL = 0.12   # moving less than this (in hand sizes) counts as "still"
WHEEL = 0x0800
KEYUP = 0x0002
VK_CONTROL = 0x11

try:
    user32 = ctypes.windll.user32
except AttributeError:          # not Windows (only for testing)
    class _Fake:
        def mouse_event(self, *a):
            pass

        def keybd_event(self, *a):
            pass
    user32 = _Fake()


def new_zoom_state():
    return {"anchor": None, "ref_d": None, "ref_mid": None, "last_move": time.time()}


def _hand_size(hand):
    return math.hypot(hand[0].x - hand[9].x, hand[0].y - hand[9].y)


def _send_zoom(direction, clicks):
    """Ctrl + mouse wheel. direction: +1 = zoom in, -1 = zoom out."""
    user32.keybd_event(VK_CONTROL, 0, 0, 0)                      # hold Ctrl
    try:
        user32.mouse_event(WHEEL, 0, 0, direction * 120 * clicks, 0)
    finally:
        user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)              # let go of Ctrl


def zoom_step(hand_a, hand_b, zs, now=None):
    """Call once per frame while two open hands are seen. Returns a short text."""
    now = time.time() if now is None else now
    size = (_hand_size(hand_a) + _hand_size(hand_b)) / 2
    if size <= 0:
        return "ZOOM"
    d = math.hypot(hand_a[0].x - hand_b[0].x, hand_a[0].y - hand_b[0].y) / size
    mid = ((hand_a[0].x + hand_b[0].x) / 2 / size, (hand_a[0].y + hand_b[0].y) / 2 / size)

    if zs["anchor"] is None:                                     # the hands just appeared
        zs["anchor"], zs["ref_d"], zs["ref_mid"], zs["last_move"] = d, d, mid, now
        return "ZOOM: move the hands apart or together"

    # are the hands still? (the keyboard command needs this)
    if abs(d - zs["ref_d"]) > STILL_TOL or math.hypot(mid[0] - zs["ref_mid"][0],
                                                      mid[1] - zs["ref_mid"][1]) > STILL_TOL:
        zs["ref_d"], zs["ref_mid"], zs["last_move"] = d, mid, now

    # zoom clicks
    change = d - zs["anchor"]
    clicks = int(abs(change) // STEP)
    if clicks == 0:
        return "ZOOM: move the hands apart or together"
    raw = 1 if change > 0 else -1
    zs["anchor"] += raw * clicks * STEP
    zs["last_move"] = now
    direction = raw * SIGN
    _send_zoom(direction, clicks)
    return "ZOOM IN" if direction > 0 else "ZOOM OUT"
