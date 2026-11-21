# Hand Gesture Control

Control your computer with hand gestures. This is my capstone project for the General Assembly Data Science Bootcamp.

## What it does
The webcam sees my hand. MediaPipe finds 21 points on the hand. A Random Forest model learns the gesture from these points. The computer can then do an action for each gesture. It helps when someone cannot use the keyboard or the mouse.

## The 7 gestures (trained with the model)

| Gesture | Action |
|---|---|
| open_palm | Make a new folder |
| victory | Make a new text file |
| ok | Write a line of text in the file |
| fist | Close the window |
| thumbs_up | Type "Yes" |
| thumbs_down | Type "No" |
| call_me | Prepare a "please call me" email (victory = send, fist = cancel) |

## More gestures (hand shape rules, hands-free mode)
These use simple finger rules (which fingers are up or down), not the model. They are part of the full computer-control app.

| Hand shape | Action |
|---|---|
| Index finger only | Move the mouse |
| Pinch (thumb + index) and release | Left click |
| Index + pinky (horns) | Right click |
| Index + middle fingers | Scroll up and down |
| Index + middle + ring fingers | Volume (turn the hand like a knob) |
| Two open hands | Open the on-screen keyboard |
| Two fists | Voice note (Windows voice typing) |

## What is in the notebook

Hand_Gesture_Capstone.ipynb shows the full data science work, step by step:

1. Collect the data: the webcam records 100 frames per gesture in several sessions.
2. Make features: MediaPipe gives 21 points. We subtract the wrist and divide by the biggest number, so the position and the size of the hand do not matter (42 numbers per frame).
3. Explore the data: 7 gestures x 4 sessions x 100 frames = 2800 rows.
4. Train a Random Forest (100 trees).
5. Test it honestly on a session the model never saw.

## Results
- Train on sessions 1-3, test on session 4: **97%** accuracy.
- Train on session 1, test on session 2: **88%**.
- Chance level is **14%** (1 of 7 gestures).
- The weakest gesture is thumbs_up, because the model sometimes mixes it with call_me.

## How a command is protected from mistakes
A command runs only if the model is at least 80% sure, the same gesture is held for 8 frames in a row, and 3 seconds passed since the last command.

## Run the notebook
```
pip install -r requirements.txt
jupyter notebook Hand_Gesture_Capstone.ipynb
```
The notebook needs two files in the same folder:
- `hand_landmarker.task`: the pre-trained MediaPipe hand landmark model (Google). It can be downloaded from the MediaPipe documentation.
- `gestures.csv`: the data. It is created by the recording cells of the notebook.

Do not use "Run All": the recording cells open the camera and write a new gestures.csv.

## Limits
- The model was trained on my hand, with my camera and light. Other people and other light can give lower accuracy.
- The computer-control part works on Windows only.

## Credits
- MediaPipe (Google) for the hand landmarks.
- I used Claude (Anthropic) as an AI assistant to help me with code and explanations, and I studied and tested the project myself.
