# 🚗 Safe Steer AI — Presentation Guide
### A Driver Safety Monitoring System
**Prepared by: Athira**

---

## 🌟 What is Safe Steer?

Safe Steer is a **real-time AI-powered driver monitoring system** that watches a driver's face and hands using a camera, and raises smart alerts when it detects drowsiness or mobile phone usage while driving.

Think of it as a **digital co-pilot** sitting next to you — always watching, never sleeping — ready to shout "Wake up!" before an accident happens.

---

## 🛠️ Technologies Used — In Simple Words

### 1. 🐍 Python
**What it is:** The main programming language used to build the entire system.

**Simple Explanation:** Python is like English for computers. It is easy to read and write, and has thousands of ready-made tools (called "libraries") that make it perfect for AI projects. Everything in Safe Steer — from capturing camera video to saving incident records — is written in Python.

---

### 2. 🌐 Flask (Web Framework)
**What it is:** A lightweight tool to build websites and web applications in Python.

**Simple Explanation:** Flask is the engine that runs the Safe Steer website. When you open the app in a browser, log in, or view the dashboard, Flask is handling all of that behind the scenes. It acts as the "waiter" between the user (browser) and the kitchen (database + AI logic).

**Used for:**
- Login / Signup pages
- Driver Dashboard
- Admin Panel
- Starting the monitoring camera

---

### 3. 📸 OpenCV (Computer Vision)
**What it is:** Open Source Computer Vision Library — a tool for processing images and video from a camera.

**Simple Explanation:** OpenCV is what lets Safe Steer "see" the world through the camera. Every time the camera captures a frame (picture), OpenCV reads it, converts it to a format the AI can understand (RGB colour), and displays the live video window on screen with alert messages drawn on top.

**Used for:**
- Capturing live video from the webcam
- Converting colour formats (BGR to RGB)
- Drawing text and overlays on the video feed

---

### 4. 🤖 MediaPipe (Google's AI Library)
**What it is:** A Google-built AI framework for detecting faces, hands, and body in real time.

**Simple Explanation:** MediaPipe is the "AI brain" that looks at each camera frame and finds the exact positions of 468 dots (called landmarks) on the driver's face, plus 21 dots on each hand. It does this up to 30–60 times per second. Safe Steer uses these dot positions to calculate whether eyes are open or closed, and whether a hand is holding a phone near the face.

**Two models used:**

| Model | What it detects |
|---|---|
| FaceMesh | 468 precise points on the face (eyes, nose, lips, cheeks) |
| Hand Landmarker | 21 points on the hand (fingertips, joints, wrist) |

---

### 5. 🗄️ SQLite (Database)
**What it is:** A lightweight database built directly into the app — no separate server needed.

**Simple Explanation:** SQLite is like a digital notebook that stores all information permanently. Safe Steer uses it to store user accounts (name, email, vehicle number) and incident records (when a drowsiness or phone alert was triggered, with exact date and time).

**Stores:**
- Driver user accounts
- All safety incidents with timestamps
- Admin accounts

---

### 6. 🔊 Pygame (Sound System)
**What it is:** A Python library for playing audio and handling multimedia.

**Simple Explanation:** Whenever the AI detects a danger, it needs to play a sound alert immediately — without pausing the camera. Pygame handles all audio playback in the background, allowing multiple sounds to play at the same time without freezing the video feed.

**Used for:**
- Playing warning beeps and alarm sounds
- Playing the car horn during emergencies
- Robotic boot-up sound when the system starts

---

### 7. 🗣️ pyttsx3 (Text-to-Speech)
**What it is:** A Python library that converts written text into spoken voice — fully offline.

**Simple Explanation:** This is what makes Safe Steer "speak" to the driver. When drowsiness is detected, instead of just beeping, the system actually says things like "Warning: High driver fatigue index. Please pull over safely for a rest break." It works without internet — voice is generated directly on the device.

**Used for:**
- Boot announcement: "Safe Steer A.I. online. Driver safety radar engaged."
- Drowsiness warning voice alerts
- Phone distraction voice warnings
- Emergency announcement: "Critical emergency: Driver is unresponsive."

---

### 8. 🔢 NumPy (Math / Numerical Processing)
**What it is:** A Python library for fast mathematical operations on large arrays of numbers.

**Simple Explanation:** NumPy is used to mathematically generate the robotic sound effects (chirps, warning tones, boot sound) from scratch using sine wave equations. It also helps process the raw audio data for the Mayday voice alert effect.

---

### 9. 🔐 Werkzeug (Password Security)
**What it is:** A security library used by Flask for hashing passwords.

**Simple Explanation:** When a user creates an account, their password is never stored as plain text. Werkzeug converts it into a scrambled code (called a hash) that cannot be reversed. When logging in, it checks if the entered password matches that scrambled code — keeping accounts safe even if the database is accessed.

---

## 🧠 Algorithms — In Simple Words

### Algorithm 1: EAR — Eye Aspect Ratio
**What it does:** Detects if the driver's eyes are closed (drowsiness detection).

**Simple Explanation:**
EAR stands for Eye Aspect Ratio. The AI places 6 dots around each eye. It then calculates a ratio:
- Eye open → the dots are spread apart → EAR value is HIGH (around 0.3+)
- Eye closed → the dots are squeezed together → EAR value is LOW (around 0.1–0.18)

**The formula (just measuring distances between eye landmark dots):**

```
EAR = (vertical height 1 + vertical height 2) / (2 x horizontal width)
```

When EAR drops below **0.18** for more than **18 consecutive frames** (about 0.7 seconds), Safe Steer decides the driver has closed their eyes too long and triggers an alert.

**Eye landmark points used:**
- Left Eye: face landmarks 362, 385, 387, 263, 373, 380
- Right Eye: face landmarks 33, 160, 158, 133, 153, 144

---

### Algorithm 2: Euclidean Distance — Phone Usage Detection
**What it does:** Detects if the driver is holding a phone near their face.

**Simple Explanation:**
The system measures the straight-line distance between:
1. The thumb tip and the nose
2. The index fingertip and the nose

If either hand is too close to the face (distance less than 100 pixels) AND the thumb and index finger are spread apart (not pinching), it likely means the driver is holding a phone near their ear or face.

**The formula (just like measuring a straight line on a map):**

```
distance = square root of ((x2 - x1) squared + (y2 - y1) squared)
```

If this pattern continues for **120 frames (about 4–5 seconds)**, a "Phone Usage" alert is triggered.

---

### Algorithm 3: Alert Escalation Logic
**What it does:** Decides how severe the situation is and chooses the right response.

**Simple Explanation:**
Safe Steer does not just shout immediately — it watches a pattern before deciding how serious things are:

```
Stage 1: Eyes closed for 0.7s         → Play Mayday alert sound + voice
Stage 2: 3 Mayday alerts in a row      → Emergency: car horn + voice + incident logged
Stage 3: 3 drowsy episodes total       → Fatigue reminder: "Please pull over and rest"
```

This is a **rule-based decision tree** — a classic AI technique where the system follows pre-defined "if this, then do that" rules based on observed conditions.

---

### Algorithm 4: Audio Signal Synthesis
**What it does:** Generates robotic sound effects using mathematics.

**Simple Explanation:**
Instead of downloading sound files, Safe Steer generates its own sound effects using a mathematical technique called sine wave synthesis:

- A sine wave is a smooth, repeating oscillation — the basic building block of sound
- By combining multiple sine waves at different frequencies and speeds, the system creates chirps, warning beeps, emergency klaxons, and boot sounds
- The Mayday voice is further processed with ring modulation (multiplying the voice signal with a 55 Hz oscillator) to make it sound robotic and urgent

---

## 🔄 How It All Works Together — The Full Flow

```
Camera
    |
OpenCV captures each frame (30 times per second)
    |
MediaPipe FaceMesh → 468 face landmarks detected
MediaPipe HandLandmarker → 21 hand landmarks detected
    |
    |-- EAR Algorithm ----> Eyes closing? ---> Drowsiness alert
    |-- Distance Algorithm -> Hand near face? -> Phone alert
    |
Audio Alerts (Pygame + pyttsx3) → Sound + Voice warnings
    |
SQLite Database → Log the incident with timestamp
    |
Flask Web Dashboard → Driver / Admin can review all incidents
```

---

## 🚨 Alert Types — What Happens When

| Situation Detected | Alert Triggered |
|---|---|
| Eyes closed for about 0.7 seconds | "Mayday! Mayday! You are in danger!" |
| 3 Mayday alerts in a row | Car horn + emergency voice + DB log |
| 3 drowsy episodes total | "Please pull over for a rest break" |
| Phone near face for 4–5 seconds | "Handheld mobile distraction detected" |
| System starts up | "Safe Steer A.I. online. Safety radar engaged." |
| Eyes reopen after closing | Safe recovery chime sound |

---

## 🏗️ System Architecture

```
+------------------------------------------+
|             Web Browser                  |
|   Login / Dashboard / Admin Panel        |
+------------------+-----------------------+
                   |
+------------------v-----------------------+
|          Flask Web Server                |
|   (app.py — routes, sessions, auth)     |
+-------+----------------------------------+
        |                  |
+-------v------+   +-------v------------------+
| SQLite DB    |   |   monitor.py (AI Core)   |
| (safesteer   |   |   OpenCV + MediaPipe     |
|   .db)       |   |   EAR + Distance Algo    |
+--------------+   +-------+------------------+
                           |
                   +-------v------------------+
                   |   audio_alerts.py        |
                   |   Pygame + pyttsx3       |
                   |   Sound + Voice AI       |
                   +--------------------------+
```

---

## 📋 Project Summary Card

| Feature | Technology |
|---|---|
| Programming Language | Python 3.x |
| Web Framework | Flask + Flask-CORS |
| AI / Computer Vision | Google MediaPipe |
| Camera Processing | OpenCV |
| Drowsiness Algorithm | Eye Aspect Ratio (EAR) |
| Phone Detection Algorithm | Euclidean Distance |
| Database | SQLite |
| Audio Playback | Pygame |
| Voice Alerts | pyttsx3 (Text-to-Speech) |
| Math Processing | NumPy |
| Password Security | Werkzeug |
| Frontend Styling | CSS (Glassmorphism Design) |

---

## 💡 Key Takeaways for the Presentation

1. **No internet needed** — Everything runs fully offline on the device
2. **Real-time** — Processes 30 frames per second, detecting danger in under 1 second
3. **Multi-modal alerts** — Sound + Voice + Visual warning all at the same time
4. **Scalable** — Admin panel can monitor multiple drivers across a fleet
5. **Forensic logging** — Every incident is timestamped and stored for later review
6. **AI that speaks** — The system communicates with the driver in plain language

---

*Safe Steer AI — Making Roads Safer, One Frame at a Time*
