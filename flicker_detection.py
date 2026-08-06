"""
Screen-flicker detection for anti-spoofing.

Physical screens (phones, tablets, monitors) emit light at their refresh rate,
causing a subtle periodic brightness oscillation in the face region that a real
face does not have. This module tracks average face brightness over time and
uses FFT to detect high-frequency periodic oscillations.
"""

from collections import deque
import cv2
import numpy as np
import config


class FlickerTracker:
    """Tracks average face brightness across frames for one face 'slot' and
    detects unnatural high-frequency periodic oscillation via real FFT."""

    def __init__(self, buffer_size=config.FLICKER_BUFFER_SIZE,
                 magnitude_threshold=config.FLICKER_MAGNITUDE_THRESHOLD):
        self.buffer_size = buffer_size
        self.magnitude_threshold = magnitude_threshold
        self.brightness_history = deque(maxlen=self.buffer_size)
        self.looks_like_screen = False
        self.peak_freq = 0.0
        self.peak_mag = 0.0

    def update(self, face_bgr, fps_estimate=30.0):
        """
        Updates rolling brightness history with the current face crop and checks
        for periodic screen flicker.

        Returns:
            bool: True if suspicious periodic screen flicker pattern is detected,
                  False if it looks like natural lighting variation.
        """
        if face_bgr is None or face_bgr.size == 0:
            return self.looks_like_screen

        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        self.brightness_history.append(mean_brightness)

        if len(self.brightness_history) < self.buffer_size:
            self.looks_like_screen = False
            self.peak_freq = 0.0
            self.peak_mag = 0.0
            return False

        # Zero-center the brightness sequence to remove DC (0 Hz) offset
        arr = np.array(self.brightness_history, dtype=np.float64)
        arr = arr - np.mean(arr)

        # Compute real FFT of the sequence
        fft_vals = np.fft.rfft(arr)
        fft_mags = np.abs(fft_vals)

        # Index 0 is DC (0 Hz), Index 1 is very low frequency natural drift (e.g. head movement).
        # We check higher frequencies (indices >= 2) for unnatural periodic oscillations.
        if len(fft_mags) > 2:
            high_freq_mags = fft_mags[2:]
            peak_idx_in_high = int(np.argmax(high_freq_mags))
            peak_mag = float(high_freq_mags[peak_idx_in_high])
            peak_freq_bin = peak_idx_in_high + 2

            # Convert bin to approximate frequency in Hz relative to camera frame rate
            self.peak_freq = float((peak_freq_bin / self.buffer_size) * fps_estimate)
            self.peak_mag = peak_mag
            self.looks_like_screen = bool(self.peak_mag > self.magnitude_threshold)
        else:
            self.looks_like_screen = False
            self.peak_freq = 0.0
            self.peak_mag = 0.0

        return self.looks_like_screen

    def reset(self):
        self.brightness_history.clear()
        self.looks_like_screen = False
        self.peak_freq = 0.0
        self.peak_mag = 0.0
