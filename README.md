# Hand Gesture Control

Control your computer with hand gestures. This is my capstone project for the General Assembly Data Science Bootcamp.

**Live web demo:** _(paste your Streamlit link here)_  
**Video walkthrough:** _(paste your video link here)_

## What it does
The webcam sees my hand. MediaPipe finds 21 points on the hand. A Random Forest model learns the gesture. The computer then does an action: it makes a folder or a file, writes text, says Yes or No, sends an "I need help, please call me" email, moves the mouse, scrolls, and changes the volume. It helps when someone cannot use the keyboard or the mouse.

## Two apps
| App | Where it runs | What it shows |
|---|---|---|
| `web_demo.py` | Web (Streamlit Cloud) | Take a photo of your hand: it shows the gesture, the confidence, and the action |
| `app_v2.py` | Your own Windows computer with a webcam | The full app: live camera and real control of the computer |

A website cannot control your computer, so the full app runs locally and the web demo shows the recognition part.

## Gestures
| Gesture | Action |
|---|---|
| Open palm | New folder |
| Victory (hold 1 second) | New file and open it. Also SEND for a waiting email |
| OK | Write the next line in the file |
| Fist | Close the file window. Also CANCEL for a waiting email |
| Thumbs up / thumbs down | Say "Yes" / "No" |
| Call me | Prepare the email "Call me now" (victory = send, fist = cancel) |
| Two open hands | On-screen keyboard |
| Two fists | Voice note: new file and start voice typing (Win+H) |

The hand shape chooses the mode, so everything works at the same time:

| Hand shape | Action |
|---|---|
| Index finger up | Mouse: move. Pinch thumb and index = click. Hold the pinch = drag |
| Index and pinky up | Right click |
| Index and middle up | Scroll (move the hand up or down) |
| Index, middle and ring up | Volume (turn the hand) |

Gestures can be changed in the "Customize gestures" box (for example victory = open Outlook).

## How it works
1. MediaPipe HandLandmarker finds 21 points on the hand.
2. We subtract the wrist and divide by the biggest number: 42 numbers that do not depend on where the hand is or how big it looks.
3. **Feature selection:** we keep only the 5 fingertips (10 numbers). Accuracy is 97.2%, the same as all 42 numbers (about 97%).
4. A Random Forest (100 trees) predicts the gesture.
5. A command runs only if the model is at least 80% sure, the gesture is held for 8 frames, and 3 seconds passed since the last command.

## Data and results
- 7 gestures x 4 sessions x 100 frames = 2800 rows (`gestures.csv`), recorded by me.
- Accuracy: **97%** (train on sessions 1-3, test on session 4). Chance level is 14% (1 of 7).
- Train on session 1 and test on session 2: 88%.
- Mouse, scroll, volume and the two-hand gestures use simple rules about which fingers are up (`poses.py`). They are not trained.

## Run it
```
pip install -r requirements.txt
streamlit run web_demo.py      # web demo
streamlit run app_v2.py        # full app (Windows, webcam)
```
To record more data (for example in a new room): `python record_more_data.py`.
In `commands.py`, change `DEFAULT_TO` to your own email for the email feature.

## Files
| File | What it is |
|---|---|
| `app_v2.py` | The full Streamlit app |
| `commands.py`, `commands_v2.py` | Features, debounce, actions, settings |
| `poses.py` | Which fingers are up (hand shapes) |
| `mouse_mode_v2.py`, `scroll_mode.py`, `volume_mode.py` | Mouse, scroll, volume |
| `web_demo.py`, `web_core.py` | The web demo |
| `record_more_data.py` | Record more gesture data |
| `Hand_Gesture_Capstone.ipynb` | Data collection, features, model, accuracy |
| `Hand_Gesture_Dataset.ipynb` | Ready dataset (HaGRID) and feature selection |
| `gestures.csv`, `hand_landmarker.task` | My data and the MediaPipe model |

## Limits
- The full app works on Windows only (it uses Windows features).
- The model was trained on my hand, in my rooms. Other people and other light may give lower accuracy.
- The ready dataset notebook (HaGRID) is written but not fully tested on real images.
- Sending the email with Outlook is not fully tested.

## Credits
- MediaPipe (Google) for hand landmarks.
- HaGRID dataset, license CC BY-SA 4.0 (ready dataset notebook).
- I used Claude (Anthropic) as an AI assistant to help me with code and explanations, and I studied and tested the project myself.
