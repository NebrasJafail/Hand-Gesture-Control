"""
poses.py  -  simple RULES (no training) that look at which fingers are up.

Why? We want the mouse, the volume and the commands to work AT THE SAME TIME
without touching the laptop. The hand shape tells the program what you want:

   ☝️  POINT  (only index up)              -> MOUSE  (move, click, drag)
   🤘  HORNS  (index + pinky up)           -> RIGHT CLICK
   ✌️  TWO    (index + middle up)          -> SCROLL (move the hand up / down)
                                              (hold it still for 1 second = victory command)
   3 fingers  (index + middle + ring up)   -> VOLUME knob (turn the hand)
   any other shape (open palm, fist, ...)  -> normal gesture COMMANDS (the model)
   👐  two open hands                      -> "two_open_hands" command (on-screen keyboard)
   ✊✊ two fists                           -> "two_fists" command (voice note)

How do we know a finger is up?
   ratio = (distance wrist -> fingertip) / (distance wrist -> middle joint of that finger)
   finger up   : ratio is big   (we measured about 1.3 on our own data)
   finger down : ratio is small (we measured about 0.5 to 0.9 on our own data)
The thumb is ignored (it is hard to judge, and we use it for clicking).
"""
import math

FINGERS = {"index": (6, 8), "middle": (10, 12), "ring": (14, 16), "pinky": (18, 20)}  # (joint, tip)
UP = 1.2           # ratio above this = finger up
DOWN = 1.0         # ratio below this = finger down
STAY_UP = 0.85     # when we are ALREADY in a pose, we are more forgiving
STAY_DOWN = 1.1    # (for example the index bends a little while you pinch)
TWO_SPREAD_MAX = 0.50   # TWO (scroll): the gap between index and middle tips / hand size must be SMALLER than this
TWO_SPREAD_STAY = 0.65  # when already scrolling, a little more forgiving
                        # a wide gap (a real V sign) is NOT scroll -> it stays "victory"
ENTER_FRAMES = 5   # a pose must be held this many frames before it starts (about 0.17 s)

POSES = {
    "POINT": (True, False, False, False),    # index, middle, ring, pinky
    "HORNS": (True, False, False, True),
    "TWO": (True, True, False, False),       # same shape as victory: see app_v2.py
    "THREE": (True, True, True, False),
}


def _dist(hand, a, b):
    return math.hypot(hand[a].x - hand[b].x, hand[a].y - hand[b].y)


def finger_states(hand, relaxed=False):
    """Returns [index, middle, ring, pinky] with True (up), False (down) or None (not sure)."""
    up, down = (STAY_UP, STAY_DOWN) if relaxed else (UP, DOWN)
    states = []
    for joint, tip in FINGERS.values():
        ratio = _dist(hand, 0, tip) / _dist(hand, 0, joint)
        if ratio >= up:
            states.append(True)
        elif ratio <= down:
            states.append(False)
        else:
            states.append(None)
    return states


def pose_name(hand, current=None):
    """POINT / HORNS / TWO / THREE or None. 'current' = the pose we are in now (more forgiving)."""
    wanted_current = POSES.get(current)
    if wanted_current is not None:
        # still the same pose? (relaxed rules)
        if tuple(finger_states(hand, relaxed=True)) == wanted_current:
            if current != "TWO" or tip_gap(hand) < TWO_SPREAD_STAY:
                return current
    states = tuple(finger_states(hand))
    for name, shape in POSES.items():
        if states == shape:
            if name == "TWO" and tip_gap(hand) >= TWO_SPREAD_MAX:
                return None          # fingers far apart = victory sign, not scroll
            return name
    return None


def new_pose_state():
    return {"candidate": None, "count": 0, "active": None}


def update_pose(ps, hand):
    """Call once per frame. Returns the pose that is ACTIVE now (held long enough), or None."""
    name = pose_name(hand, ps["active"])
    if name == ps["candidate"]:
        ps["count"] += 1
    else:
        ps["candidate"], ps["count"] = name, 1
    if name is not None and (ps["count"] >= ENTER_FRAMES or name == ps["active"]):
        ps["active"] = name
    else:
        ps["active"] = None
    return ps["active"]


def two_hand_gesture(hand_a, hand_b):
    """Both hands open -> 'two_open_hands'. Both hands fists -> 'two_fists'. Else None."""
    a, b = finger_states(hand_a), finger_states(hand_b)
    if all(s is True for s in a + b):
        return "two_open_hands"
    if all(s is False for s in a + b):
        return "two_fists"
    return None


def hand_size(hand):
    return _dist(hand, 0, 9)


def tip_gap(hand):
    """Gap between the index tip (8) and the middle tip (12), measured in hand sizes."""
    return _dist(hand, 8, 12) / hand_size(hand)


def fix_thumb_label(hand, label):
    """The model mixes thumbs_up and call_me. The PINKY tells them apart (a simple rule):
       pinky up   -> call_me      pinky down -> thumbs_up.   (thumbs_down is left to the model)"""
    if label not in ("thumbs_up", "call_me"):
        return label
    idx, mid, ring, pinky = finger_states(hand)
    if idx is True or mid is True or ring is True:     # other fingers up: not one of these two
        return label
    if pinky is True:
        return "call_me"
    if pinky is False:
        return "thumbs_up"
    return label
