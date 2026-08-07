"""
Central configuration for the smart attendance system.
Tune these values to your camera/lighting after testing.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")

# Face matching: face_recognition's face_distance is 0 (identical) to ~1 (very different).
# Library default tolerance is 0.6; we go a bit stricter to cut down false accepts.
KNOWN_FACES_TOLERANCE = 0.45

# --- Liveness / anti-spoof settings ---
# Eye Aspect Ratio below this = eye considered "closed" for that frame.
BLINK_EAR_THRESHOLD = 0.21
# Consecutive closed-eye frames required before counting it as a real blink.
BLINK_CONSEC_FRAMES = 2
# Minimum "looks-real" texture score (0-1) required in addition to a detected blink.
TEXTURE_SCORE_MIN = 0.35

# --- Flicker detection settings ---
# Rolling buffer size (number of frames) of average face brightness to collect for FFT.
FLICKER_BUFFER_SIZE = 15
# Threshold for FFT high-frequency peak magnitude to flag as screen flicker.
# NOTE: This needs empirical calibration against a real face vs. a phone screen
# on the actual deployment camera, same as TEXTURE_SCORE_MIN already is.
FLICKER_MAGNITUDE_THRESHOLD = 20.0

# --- Model-based Anti-Spoofing settings ---
# Path to pretrained ONNX anti-spoofing model (e.g., Silent-Face-Anti-Spoofing MiniFASNet).
ANTI_SPOOF_MODEL_PATH = "models/MiniFASNetV2.onnx"
# Minimum confidence score (0-1) from the anti-spoofing model to consider a face live.
MODEL_LIVENESS_THRESHOLD = 0.6

# Don't log the same employee again within this many seconds (prevents duplicate
# punches from a person lingering in front of the camera).
DUPLICATE_PUNCH_COOLDOWN_SECONDS = 30

# How long (seconds) the employee-details banner stays on screen after a match.
DISPLAY_SECONDS = 3

SNAPSHOT_DIR = "unknown_snapshots"

# --- Attendance / Shift Tracking settings ---
# Standard working shift duration (hours) for overtime calculation.
STANDARD_SHIFT_HOURS = 9.0
# Minimum working shift duration (hours) before triggering an under-shift alert.
MIN_SHIFT_HOURS = 8.0

