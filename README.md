<p align="center"><img src="wavely_logo.jpg" width="600" alt="Wavely logo"></p>

# Hand Gesture Control

Control your computer with hand gestures. This is my capstone project for the General Assembly Data Science Bootcamp.

## What it does
The webcam sees my hand. MediaPipe finds 21 points on the hand. A Random Forest model learns the gesture from these points. The computer can then do an action for each gesture (for example: make a folder, write text, say "Yes" or "No", or send a "please call me" email). It helps when someone cannot use the keyboard or the mouse.

## The 7 gestures
`open_palm`, `victory`, `ok`, `fist`, `thumbs_up`, `thumbs_down`, `call_me`

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

## Limits
- The model was trained on my hand, with my camera and light. Other people and other light can give lower accuracy.
- The computer-control part works on Windows only.

## Credits
- MediaPipe (Google) for the hand landmarks.
