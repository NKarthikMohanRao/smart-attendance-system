"""
Anti-spoofing helpers.

Two independent, lightweight signals are combined:

1. Blink detection via Eye Aspect Ratio (EAR) on face_recognition's landmarks.
   A printed photo or a static image on a phone screen cannot blink, so
   requiring a real blink before accepting a match blocks the simplest
   "hold up a photo" attack.

2. Texture/sharpness scoring. Printed photos and re-photographed screens
   typically lose high-frequency detail and show different color-channel
   statistics than a real face under the same camera. This is a heuristic,
   not a certified liveness check — see README for its limits.
"""

import numpy as np
import cv2
import face_recognition
from scipy.spatial import distance as dist
import config


def eye_aspect_ratio(eye_points):
    eye_points = np.array(eye_points)
    a = dist.euclidean(eye_points[1], eye_points[5])
    b = dist.euclidean(eye_points[2], eye_points[4])
    c = dist.euclidean(eye_points[0], eye_points[3])
    return (a + b) / (2.0 * c)


def get_ear_for_face(rgb_frame, face_location):
    """Returns the average eye-aspect-ratio for a given face box, or None
    if landmarks couldn't be extracted (e.g. face at a bad angle)."""
    landmarks_list = face_recognition.face_landmarks(rgb_frame, [face_location])
    if not landmarks_list:
        return None
    landmarks = landmarks_list[0]
    if "left_eye" not in landmarks or "right_eye" not in landmarks:
        return None
    left_ear = eye_aspect_ratio(landmarks["left_eye"])
    right_ear = eye_aspect_ratio(landmarks["right_eye"])
    return (left_ear + right_ear) / 2.0


def texture_liveness_score(face_bgr):
    """Rough 0-1 'looks-real' score based on sharpness + color-channel spread.
    Not a guarantee on its own — always combine with blink detection."""
    if face_bgr is None or face_bgr.size == 0:
        return 0.0

    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Divisor tuned empirically for a typical laptop webcam at ~40-60cm.
    # Re-tune per your camera: print the raw laplacian_var for a real face
    # vs. a printed photo and pick a divisor between the two.
    sharpness_score = min(laplacian_var / 150.0, 1.0)

    b, g, r = cv2.split(face_bgr)
    color_std = float(np.std([b.std(), g.std(), r.std()]))
    color_score = min(color_std / 20.0, 1.0)

    return 0.7 * sharpness_score + 0.3 * color_score


def model_based_liveness_score(face_bgr):
    """
    Returns 0-1 'real face' confidence score using a trained anti-spoofing
    model (MiniFASNet via ONNX), falling back gracefully to texture_liveness_score
    if the model is missing or fails to load.
    """
    from anti_spoof_model import model_based_liveness_score as _model_fn
    return _model_fn(face_bgr, fallback_fn=texture_liveness_score)



class BlinkTracker:
    """Tracks EAR across frames for one face 'slot' and confirms once a
    real blink (closed then reopened) has occurred."""

    def __init__(self, ear_threshold=config.BLINK_EAR_THRESHOLD,
                 consec_frames=config.BLINK_CONSEC_FRAMES):
        self.ear_threshold = ear_threshold
        self.consec_frames = consec_frames
        self.counter = 0
        self.blinked = False

    def update(self, ear):
        if ear is None:
            return self.blinked
        if ear < self.ear_threshold:
            self.counter += 1
        else:
            if self.counter >= self.consec_frames:
                self.blinked = True
            self.counter = 0
        return self.blinked

    def reset(self):
        self.counter = 0
        self.blinked = False
