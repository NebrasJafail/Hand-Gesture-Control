"""
app_v2.py  -  version 2 of the Streamlit app (the original app.py is NOT changed).

New in v2:
  - HANDS-FREE: camera, control, mouse and volume are all ON when the app starts.
    The HAND SHAPE chooses what happens (see poses.py):
      point (index up) = mouse | horns (index + pinky) = right click
      two fingers (index + middle) = volume knob | anything else = gesture commands | 2 hands = special commands
  - the model uses only the fingertip numbers (feature selection)
  - a button for the on-screen keyboard and a button for voice typing
  - a "Customize" box: link any gesture to any action or app/website
  - mouse mode shows ACTIVE / PAUSED / DRAGGING

Run it with:  streamlit run app_v2.py     (or double-click run_gesture_v2.bat)
"""
import os
import time

import cv2
import mediapipe as mp
import pandas as pd
import streamlit as st
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import commands_v2 as gc2        # actions, settings, feature selection
import commands as gc            # debounce logic and shared state (original file)
import wavely_cursor as cur         # the glowing cursor
import wavely_ui as ui           # the look of the app (colors, logo, pictures)
import mouse_mode_v2 as mm       # mouse mode v2
import poses                     # rules: which fingers are up
import scroll_mode as sm         # scroll with two fingers
import volume_mode as vm         # volume mode: thumb + index distance = volume
import zoom_mode as zm           # zoom with two open hands (apart = in, together = out)

VICTORY_STILL = 1.0   # seconds without scrolling before the victory command may run
KEYBOARD_STILL = 1.0  # two open hands must be STILL this long before the keyboard opens (else it is zoom)
PREDICT_EVERY = 3     # the model looks at 1 frame out of 3 (the instructor's tip: do not send every frame)
SHOW_EVERY = 2        # the picture on the page updates every 2nd frame

camera_number = 0
backend = "Default"   # or "DirectShow"

st.set_page_config(page_title="Wavely", page_icon="👋", layout="wide")

GESTURES = ["open_palm", "victory", "ok", "fist", "thumbs_up", "thumbs_down", "call_me",
            "two_open_hands", "two_fists"]
EMOJI = {"open_palm": "✋", "victory": "✌️", "ok": "👌", "fist": "✊",
         "thumbs_up": "👍", "thumbs_down": "👎", "call_me": "🤙",
         "two_open_hands": "👐", "two_fists": "✊✊"}


def gestures_table():
    """The table of all gestures and what each one does (it follows the saved settings)."""
    rows = []
    for g in GESTURES:
        link = gc2.SETTINGS["gestures"][g]
        text = gc2.ACTION_LABELS.get(link["action"], link["action"])
        if link["action"] == "open_app" and link["target"]:
            text += ": " + link["target"]
        rows.append(text)
    shape_names = ["☝️ Point (index up)", "🤘 Horns (index + pinky up)",
                   "✌️ Two fingers (index + middle)", "3 fingers (index + middle + ring)",
                   "👐 Two open hands, moving"]
    shape_actions = ["Mouse: move; pinch thumb + index = click; hold the pinch = drag",
                     "Right click",
                     "Scroll: move the hand up or down (hold still 1 s = victory: new file)",
                     "Volume: turn the hand right = louder, left = quieter",
                     "Zoom: hands apart = zoom in, hands together = zoom out (hold still 1 s = keyboard)"]
    return pd.DataFrame({
        "Gesture": shape_names + [EMOJI[g] + " " + g.replace("_", " ") for g in GESTURES],
        "Action": shape_actions + rows,
    })


# ---- the look of the app: Wavely (colors, background, logo, picture) ----
dark = st.session_state.get("dark", True)
ui.inject(dark)
cur.inject(st.session_state.get("glow", True), dark)
with ui.nav_box():
    brand_col, mode_col, help_col = st.columns([6, 2, 2])
    brand_col.markdown(ui.nav_html(dark), unsafe_allow_html=True)
    mode_col.toggle("Dark mode", value=True, key="dark")
    if hasattr(st, "popover"):                   # newer Streamlit: the button opens the table
        with help_col.popover("📋 Gestures table"):
            st.markdown("**Gestures**")
            st.table(gestures_table())
    else:                                        # older Streamlit: a box that opens
        with help_col.expander("📋 Gestures table"):
            st.table(gestures_table())
st.markdown(ui.hero_html(dark), unsafe_allow_html=True)
st.markdown('<div class="wv-section">LIVE CONTROL</div>', unsafe_allow_html=True)


@st.cache_resource
def load_model():
    return gc2.make_model()          # (model, selected columns)


@st.cache_resource
def load_detector():
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(
            model_asset_path=os.path.join(gc.BASE, "hand_landmarker.task")),
        num_hands=2,     # 2 hands, so we can see the two-hand gestures
    )
    return vision.HandLandmarker.create_from_options(options)


model, feature_cols = load_model()
detector = load_detector()

if "log" not in st.session_state:
    st.session_state.log = []

left, right = st.columns([3, 2])

with right, ui.card("controls"):
    st.subheader("Controls")
    # everything is ON at the start, so you do not need to touch the laptop
    camera_on = st.toggle("Camera on", value=True)
    control_on = st.toggle("Gesture commands", value=True)
    mouse_on = st.toggle("Mouse", value=True)
    volume_on = st.toggle("Volume", value=True)
    st.toggle("Glow cursor", value=True, key="glow")
    st.toggle("Fixed camera", value=True, key="sticky")
    zoom_on = st.toggle("Zoom (two hands)", value=True)
    st.caption("The hand shape chooses what happens, so all of them can be ON together.")

    # --- two small buttons (they run once when pressed) ---
    b1, b2 = st.columns(2)
    if b1.button("⌨️ On-screen keyboard"):
        st.session_state.log.append(time.strftime("%H:%M:%S") + "  ⌨️ " + gc2.open_keyboard())
    if b2.button("🎤 Voice typing"):
        st.session_state.log.append(time.strftime("%H:%M:%S") + "  🎤 " + gc2.voice_typing())
    st.caption("Voice typing: click in a text box first. It uses the Windows voice "
               "typing (Win+H), so it needs internet.")

    st.caption("Click “Gestures table” at the top to see all the gestures.")

    # --- customization box ---
    with st.expander("Customize gestures"):
        with st.form("custom"):
            names = list(gc2.ACTION_LABELS.keys())
            new_links = {}
            for g in GESTURES:
                link = gc2.SETTINGS["gestures"][g]
                c1, c2 = st.columns([2, 1])
                action = c1.selectbox(EMOJI[g] + " " + g, names,
                                      index=names.index(link["action"]),
                                      format_func=lambda a: gc2.ACTION_LABELS[a],
                                      key="act_" + g)
                target = c2.text_input("App / site", value=link.get("target", ""),
                                       key="tgt_" + g,
                                       help="Only used for: Open an app or website. "
                                            "Examples: outlook, slack, teams, github.com")
                new_links[g] = {"action": action, "target": target}
            provider = st.selectbox("Email with", ["gmail", "outlook"],
                                    index=["gmail", "outlook"].index(gc2.SETTINGS["email_provider"]))
            email_to = st.text_input("Send the email to", value=gc2.SETTINGS["email_to"])
            if st.form_submit_button("Save"):
                gc2.SETTINGS["gestures"] = new_links
                gc2.SETTINGS["email_provider"] = provider
                gc2.SETTINGS["email_to"] = email_to
                gc2.save_settings(gc2.SETTINGS)
                st.success("Saved. Your choices stay after you close the app.")
    status_box = st.empty()
    log_box = st.empty()

with left, ui.card("camera"):
    st.subheader("Live camera")
    frame_box = st.empty()
    info_box = st.empty()


STATUS_CSS = ("<style>.wv-st{display:flex;gap:14px;align-items:center;padding:12px 14px;margin-top:8px;border-radius:16px;"
       "background:rgba(133,156,233,.10);border:1px solid rgba(133,156,233,.30)}"
       ".wv-st .em{font-size:30px;width:54px;height:54px;border-radius:14px;display:grid;place-items:center;flex:none;"
       "background:linear-gradient(135deg,rgba(238,170,189,.35),rgba(133,156,233,.35))}"
       ".wv-st .t{font-weight:700;font-size:16px;line-height:1.2}.wv-st .a{opacity:.75;font-size:13px;margin-top:2px}"
       ".wv-bar{height:6px;border-radius:9px;background:rgba(133,156,233,.25);margin-top:8px;overflow:hidden}"
       ".wv-bar i{display:block;height:100%;border-radius:9px;background:linear-gradient(90deg,#EEAABD,#859CE9)}"
       ".wv-chip{display:inline-block;margin:8px 6px 0 0;padding:2px 10px;border-radius:999px;font-size:12px;"
       "border:1px solid rgba(133,156,233,.45)}.wv-chip.on{background:linear-gradient(135deg,#EEAABD,#859CE9);"
       "color:#14123A;border-color:transparent}.wv-last{opacity:.7;font-size:12px;margin-top:8px}</style>")


def status_html(label, conf, hands, mode, pose):
    """The small panel under the camera: what the camera sees, the hand shape, the mode, the last action."""
    import html as _h
    if label:
        emoji = EMOJI.get(label, "🖐️")
        name = label.replace("_", " ").title()
        try:
            action = gc2.ACTION_LABELS[gc2.SETTINGS["gestures"][label]["action"]]
        except Exception:
            action = "Hand mode" if mode else ""
        pct = int(conf * 20) * 5          # steps of 5% so the panel changes less
    elif hands:
        emoji, name, action, pct = "🖐️", "Hand mode: " + (mode or "none"), "", 0
    else:
        emoji, name, action, pct = "👀", "No hand seen", "Show your hand to the camera", 0
    chips = ""
    if hands:
        chips += '<span class="wv-chip">Hand shape: <b>' + _h.escape(str(pose or "other")).upper() + "</b></span>"
    if mode:
        chips += '<span class="wv-chip on">Mode: <b>' + _h.escape(str(mode)) + "</b></span>"
    last = st.session_state.log[-1] if st.session_state.log else ""
    bar = ('<div class="wv-bar"><i style="width:%d%%"></i></div>' % pct) if pct else ""
    return ('<div class="wv-st"><div class="em">' + emoji + '</div><div style="flex:1;min-width:0">'
            '<div class="t">' + _h.escape(name) + (" · " + str(pct) + "%" if pct else "") + "</div>"
            + ('<div class="a">' + _h.escape(action) + "</div>" if action else "") + bar + "<div>" + chips + "</div>"
            + ('<div class="wv-last">Last action: ' + _h.escape(last) + "</div>" if last else "") + "</div></div>")


# the camera stays in place while the right side scrolls (the "Fixed camera" switch turns it off)
if st.session_state.get("sticky", True):
    st.markdown("""<style>
[data-testid="stColumn"]:has([class*="st-key-card"][class*="camera"]),
[data-testid="column"]:has([class*="st-key-card"][class*="camera"]){position:sticky;top:14px;align-self:flex-start}
</style>""", unsafe_allow_html=True)

st.markdown(STATUS_CSS, unsafe_allow_html=True)   # the panel style is sent ONE time (not every frame)


def show_status(mouse_text=""):   # mouse_text = what the hand is doing now (MOUSE / VOLUME ...)
    folder = gc.app_state["folder"]
    last_file = gc.app_state["last_file"]
    lines = [
        "Folder: " + (os.path.basename(folder) if folder else "none yet"),
        "Last file: " + (os.path.basename(last_file) if last_file else "none yet"),
    ]
    if mouse_text:
        lines.append("Hand mode: " + mouse_text)
    if time.time() < gc.app_state["pending_until"]:
        lines.append("Email waiting: ✌️ = SEND, ✊ = cancel")
    status_box.write("  \n".join(lines))
    log_box.write("**Log**  \n" + "  \n".join(st.session_state.log[-8:]))


show_status()

if camera_on:
    if backend == "DirectShow":
        cap = cv2.VideoCapture(camera_number, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(camera_number)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)                  # keep only the newest frame: less delay
    if not cap.isOpened():
        st.error("Could not open the camera. Close any other program using it "
                 "(for example a notebook) and turn the camera switch off and on.")
        st.stop()
    state = {"label": None, "count": 0, "last_time": 0.0}
    mouse_state = mm.new_mouse_state()
    volume_state = vm.new_volume_state()
    scroll_state = sm.new_scroll_state()
    pose_state = poses.new_pose_state()
    zoom_state = zm.new_zoom_state()
    mode, mode_text, last_mode_text = None, "", ""
    last_panel = None
    frame_no, last_pred = 0, None
    failed_reads = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                failed_reads += 1
                if failed_reads == 30:
                    info_box.error("The camera opened but gives no picture. "
                                   "Close other programs using it, then try again.")
                time.sleep(0.05)
                continue
            failed_reads = 0
            h, w = frame.shape[:2]
            frame_no += 1
            # a smaller picture for MediaPipe = faster (the 21 points are normalized: same numbers)
            rgb = cv2.cvtColor(cv2.resize(frame, (480, int(480 * h / w))), cv2.COLOR_BGR2RGB)
            result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))

            show = cv2.flip(frame, 1)
            label, conf = None, 0.0
            new_mode, pose = None, None
            hands = result.hand_landmarks
            for one_hand in hands:                       # draw every hand we see
                for p in one_hand:
                    cv2.circle(show, (int((1 - p.x) * w), int(p.y * h)), 4, (0, 255, 0), -1)
            if len(hands) >= 1:
                hand = max(hands, key=poses.hand_size)   # the bigger hand = the real one
                two = poses.two_hand_gesture(hands[0], hands[1]) if len(hands) == 2 else None
                if two is not None:
                    label, conf = two, 1.0               # two-hand gesture (rules, no model)
                else:
                    # the model looks at only 1 frame out of PREDICT_EVERY (lighter + faster);
                    # in between we keep the last answer. The hand points still update every frame.
                    if frame_no % PREDICT_EVERY == 0 or last_pred is None:
                        row = gc2.hand_to_row(hand, feature_cols)     # only the selected numbers
                        probs = model.predict_proba(row)[0]
                        best = probs.argmax()
                        last_pred = (model.classes_[best], probs[best])
                    label, conf = last_pred
                    label = poses.fix_thumb_label(hand, label)     # pinky decides: thumbs_up / call_me
                    pose = poses.update_pose(pose_state, hand)    # POINT / HORNS / TWO / THREE / None
                    if pose == "POINT" and mouse_on:
                        new_mode = "MOUSE"
                    elif pose == "HORNS" and mouse_on:
                        new_mode = "RIGHT CLICK"
                    elif pose == "TWO" and mouse_on:
                        new_mode = "SCROLL"
                    elif pose == "THREE" and volume_on:
                        new_mode = "VOLUME"
            else:
                pose_state = poses.new_pose_state()
                last_pred = None

            # leaving a mode: let go of the mouse button / reset the volume knob
            if new_mode != mode:
                if mode == "MOUSE":
                    mm.release_everything(mouse_state)
                if new_mode == "MOUSE":
                    mouse_state["x"] = None              # jump to the finger at once
                if new_mode == "VOLUME":
                    volume_state = vm.new_volume_state()
                if new_mode == "SCROLL":
                    scroll_state = sm.new_scroll_state()
                mode = new_mode
                mode_text = mode or ""
            if mode == "MOUSE":
                mode_text = "MOUSE " + mm.mouse_step(hand, mouse_state, None)
            elif mode == "RIGHT CLICK":
                if mm.pose_right_click(mouse_state):
                    st.session_state.log.append(time.strftime("%H:%M:%S") + "  🤘 right click")
                    last_mode_text = None
            elif mode == "SCROLL":
                mode_text = sm.scroll_step(hand, scroll_state)
            elif mode == "VOLUME":
                mode_text = vm.volume_step(hand, volume_state)
            # two open hands: moving apart / together = ZOOM, held still = keyboard
            if label == "two_open_hands" and zoom_on:
                mode_text = zm.zoom_step(hands[0], hands[1], zoom_state)
            else:
                zoom_state = zm.new_zoom_state()
                if mode_text.startswith("ZOOM"):
                    mode_text = ""
            if mode_text != last_mode_text:
                last_mode_text = mode_text
                show_status(mode_text)

            # gesture commands run only when the hand is NOT in the mouse / volume shape
            # The scroll pose (index + middle) looks like victory. So in that pose, victory runs
            # only if you hold it STILL for VICTORY_STILL seconds (you did not scroll).
            command_label = None if mode else label
            if label == "two_open_hands" and zoom_on \
                    and time.time() - zoom_state["last_move"] < KEYBOARD_STILL:
                command_label = None                    # the hands are moving: it is zoom, not the keyboard
            if mode == "SCROLL" and label == "victory" \
                    and time.time() - scroll_state["last_move"] >= VICTORY_STILL:
                command_label = label
            triggered = gc.update_state(state, command_label, conf, time.time())
            if triggered is not None and control_on:
                result_text = gc2.run_command(triggered)
                st.session_state.log.append(time.strftime("%H:%M:%S") + "  "
                                            + EMOJI.get(triggered, "") + " " + triggered
                                            + ": " + result_text)
                show_status(mode_text)

            if frame_no % SHOW_EVERY == 0:               # send the picture to the page every 2nd frame
                small = cv2.resize(show, (640, int(640 * show.shape[0] / show.shape[1])))
                frame_box.image(cv2.cvtColor(small, cv2.COLOR_BGR2RGB), channels="RGB", output_format="JPEG")
            panel = status_html(label, conf, hands, mode, pose)
            if panel != last_panel:                      # send the panel only when something changed
                info_box.markdown(panel, unsafe_allow_html=True)
                last_panel = panel
    finally:
        gc.close_viewer()
        cap.release()
