"""
volume_mode.py  -  volume knob with the INDEX + MIDDLE fingers (rotation).

Idea: your two fingers are like the needle of a knob.
  turn the hand to the RIGHT (clockwise, as you see yourself in the camera) = louder
  turn the hand to the LEFT  (counter-clockwise)                            = quieter

The math (2D rotation):
  1) take the point in the middle of the two fingertips (points 8 and 12)
  2) draw an arrow from the wrist (point 0) to that point
  3) angle = atan2(dy, dx)   -> the direction of the arrow in degrees
  4) every frame: change = angle now - angle before
  5) every DEG_PER_PRESS degrees of turning = one Windows volume key press (2%)
So a half turn (180 degrees) changes the volume by about 90%.

We only press the Windows volume keys (UP / DOWN), no installation. This is an early test.
"""
import ctypes
import math
import time

DEG_PER_PRESS = 4.0     # degrees of turning for one key press (= 2% volume). Smaller = more sensitive
DEAD_ZONE = 1.0         # ignore turns smaller than this (hand shake), in degrees
SIGN = 1                # if the volume goes the wrong way, change this to -1
VK_VOLUME_DOWN, VK_VOLUME_UP = 0xAE, 0xAF
KEYUP = 0x0002

try:
    user32 = ctypes.windll.user32
except AttributeError:          # not Windows (only for testing)
    class _Fake:
        def keybd_event(self, *a):
            pass
    user32 = _Fake()


def press(key, times=1):
    for _ in range(times):
        user32.keybd_event(key, 0, 0, 0)
        user32.keybd_event(key, 0, KEYUP, 0)


def new_volume_state():
    # last_angle = angle in the previous frame, spare = degrees turned but not pressed yet
    return {"last_angle": None, "spare": 0.0, "total": 0, "last_turn": time.time()}


def hand_angle(hand):
    """Direction of the arrow wrist -> middle of index and middle tips, in degrees.
    x is flipped (1 - x) because the camera picture is mirrored for the user.
    The picture's y goes DOWN, so a bigger angle = clockwise on the screen."""
    tip_x = (hand[8].x + hand[12].x) / 2
    tip_y = (hand[8].y + hand[12].y) / 2
    dx = (1 - tip_x) - (1 - hand[0].x)
    dy = tip_y - hand[0].y
    return math.degrees(math.atan2(dy, dx))


def volume_step(hand, vs):
    """Call once per frame. Returns a short text for the screen."""
    angle = hand_angle(hand)
    if vs["last_angle"] is None:
        vs["last_angle"] = angle
        return "Turn your two fingers: right = louder, left = quieter"
    change = (angle - vs["last_angle"] + 180) % 360 - 180    # fix the jump at 180 / -180
    vs["last_angle"] = angle
    if abs(change) < DEAD_ZONE:
        change = 0.0
    vs["spare"] += SIGN * change
    presses = int(abs(vs["spare"]) // DEG_PER_PRESS)
    if presses > 0:
        direction = 1 if vs["spare"] > 0 else -1
        press(VK_VOLUME_UP if direction > 0 else VK_VOLUME_DOWN, presses)
        vs["spare"] -= direction * presses * DEG_PER_PRESS
        vs["total"] += direction * presses * 2
        vs["last_turn"] = time.time()      # app_v2 uses this: while you turn, victory must not fire
    return "Volume change since start: " + ("%+d" % vs["total"]) + "%"
