"""
scroll_mode.py  -  SCROLL with two fingers (index + middle), like on a laptop touchpad.

  move the two fingers UP   = the page scrolls up
  move the two fingers DOWN = the page scrolls down

How it works:
  1) every frame we take the height (y) of the middle of the two fingertips (points 8 and 12)
  2) we divide the change by the hand size, so it works near or far from the camera
  3) we add the changes together; every time the total is one "step" we send ONE mouse-wheel click
Windows mouse wheel: mouse_event(0x0800, 0, 0, amount, 0). One click = 120.
If it scrolls the wrong way, change SIGN to -1. If it is too fast or slow, change STEP.
"""
import ctypes
import math
import time

STEP = 0.10      # hand movement (in hand sizes) for one wheel click. Smaller = faster scroll
DEAD = 0.004     # ignore tiny movements (hand shake), in hand sizes per frame
SIGN = 1         # 1 = hand up scrolls up. -1 = the opposite
WHEEL = 0x0800

try:
    user32 = ctypes.windll.user32
except AttributeError:          # not Windows (only for testing)
    class _Fake:
        def mouse_event(self, *a):
            pass
    user32 = _Fake()


def new_scroll_state():
    return {"last_y": None, "spare": 0.0, "last_move": time.time()}


def scroll_step(hand, ss):
    """Call once per frame while the two-finger shape is held. Returns a short text."""
    size = math.hypot(hand[0].x - hand[9].x, hand[0].y - hand[9].y)
    y = (hand[8].y + hand[12].y) / 2 / size
    if ss["last_y"] is None:
        ss["last_y"] = y
        return "SCROLL: move two fingers up or down"
    change = (ss["last_y"] - y) * SIGN         # up on the screen = y gets smaller = positive
    ss["last_y"] = y
    if abs(change) < DEAD:
        change = 0.0
    ss["spare"] += change
    clicks = int(abs(ss["spare"]) // STEP)
    if clicks > 0:
        direction = 1 if ss["spare"] > 0 else -1
        user32.mouse_event(WHEEL, 0, 0, direction * 120 * clicks, 0)
        ss["spare"] -= direction * clicks * STEP
        ss["last_move"] = time.time()          # app_v2 uses this: while you scroll, victory must not fire
    return "SCROLL"
