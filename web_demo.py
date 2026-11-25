"""
web_demo.py  -  LIVE WEB DEMO of the Hand Gesture Control project (Streamlit).

Why a separate web demo?
  The full app controls the user's OWN computer (folders, mouse, volume, email) with a live
  webcam, so it must run on the user's computer:   streamlit run app_v2.py
  A web server cannot control your computer. So this web page shows the recognition part:
  you take a photo of your hand, and it shows the gesture, the confidence, and the action
  that the full app would run.

Run it:  streamlit run web_demo.py
"""
import cv2
import numpy as np
import pandas as pd
import streamlit as st

import web_core as core

st.set_page_config(page_title="Hand Gesture Control", page_icon="🖐️", layout="centered")
st.title("🖐️ Hand Gesture Control")
st.caption("Control your computer with hand gestures. Capstone project, General Assembly Data Science.")


@st.cache_resource
def load_everything():
    model, cols = core.train_model()
    return model, cols, core.make_detector()


model, cols, detector = load_everything()

tab_try, tab_how, tab_gestures = st.tabs(["Try it", "How it works", "Gestures"])

with tab_try:
    st.write("Show one hand to the camera, take a photo, and see what the model sees.")
    photo = st.camera_input("Take a photo of your hand")
    upload = st.file_uploader("...or upload a photo", type=["jpg", "jpeg", "png"])
    source = photo or upload
    if source is not None:
        data = np.frombuffer(source.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        result = core.analyze(image, model, cols, detector)
        st.image(result["picture"], caption="The 21 hand points found by MediaPipe")
        if not result["found"]:
            st.warning("I could not see exactly one hand. Try again with one hand in the light.")
        else:
            label, conf = result["label"], result["confidence"]
            st.subheader(label.replace("_", " ") + "  (" + str(int(conf * 100)) + "% sure)")
            if conf < 0.8:
                st.info("The model is not sure enough (the full app needs 80%), so it would do nothing.")
            else:
                st.success("Full app action: " + core.FULL_APP_ACTION[label])
            if result["shape"]:
                st.write("Hand shape: **" + result["shape"] + "** -> " + core.SHAPE_ACTION[result["shape"]])
            st.write("Top 3 guesses:")
            st.table(pd.DataFrame(result["ranking"], columns=["Gesture", "Probability"]).round(2))

with tab_how:
    st.markdown("""
**Pipeline**

1. The camera gives a picture of the hand.
2. **MediaPipe** finds 21 points on the hand.
3. We subtract the wrist and divide by the biggest number, so the hand position and size do not matter (42 numbers).
4. **Feature selection:** we keep only the 5 fingertips (10 numbers). It gives the same accuracy (97.2%) as all 42 numbers.
5. A **Random Forest** model predicts the gesture.
6. The full app runs the action only if the model is at least **80% sure**, the gesture is held for **8 frames**, and **3 seconds** passed since the last action.

**Our data:** 7 gestures x 4 sessions x 100 frames = 2800 rows. Accuracy: **97%** (train on sessions 1-3, test on session 4).

**The full app** (runs on your own Windows computer with a webcam) also has:
mouse control, scroll, volume, voice typing, an on-screen keyboard, and a customize box.
See the README and the video demo.
""")

with tab_gestures:
    st.write("Gestures found by the model (one hand):")
    st.table(pd.DataFrame({"Gesture": list(core.FULL_APP_ACTION.keys()),
                           "Action in the full app": list(core.FULL_APP_ACTION.values())}))
    st.write("Hand shapes found by simple rules (which fingers are up):")
    st.table(pd.DataFrame({"Shape": list(core.SHAPE_ACTION.keys()),
                           "Action in the full app": list(core.SHAPE_ACTION.values())}))
