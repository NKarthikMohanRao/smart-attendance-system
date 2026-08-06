"""
Simple centroid-based multi-object tracker.

Problem this solves: the original attendance_system.py used a face's
position in that frame's detection list (0, 1, 2...) as its "identity"
for the purpose of remembering blink history. That breaks the moment
two people move around in front of the camera — position 0 in one
frame might be a different person than position 0 in the next frame,
scrambling their blink counters.

How this fixes it: each tracked face gets a permanent numeric ID. Every
new frame, we compute the center point ("centroid") of each newly
detected face box, and match it to the closest centroid we were already
tracking from recent frames (within max_distance pixels). A face that
moves a little between frames still matches its own ID; a face that
disappears for too long (max_missed_frames) gets dropped so IDs don't
leak memory forever.

This is a general-purpose pattern — reusable for any project that needs
to track multiple moving objects across video frames (people counting,
vehicle tracking, multi-object games, etc.), not just this one.
"""

from collections import OrderedDict

import numpy as np


class CentroidTracker:
    def __init__(self, max_distance=75, max_missed_frames=15):
        """
        max_distance: maximum pixel distance between an existing tracked
            centroid and a new detection for them to be considered the
            same face. Too small = same person gets a new ID if they move
            fast; too large = two different people can get merged.
            Re-tune for your camera resolution and typical movement speed.
        max_missed_frames: how many consecutive frames a tracked face can
            go undetected (e.g. turned away, briefly occluded) before we
            give up on it and free its ID for reuse.
        """
        self.next_object_id = 0
        self.objects = OrderedDict()   # object_id -> (x, y) centroid
        self.missed = OrderedDict()    # object_id -> consecutive missed-frame count
        self.max_distance = max_distance
        self.max_missed_frames = max_missed_frames

    @staticmethod
    def box_to_centroid(box):
        top, right, bottom, left = box
        cx = int((left + right) / 2.0)
        cy = int((top + bottom) / 2.0)
        return (cx, cy)

    def register(self, centroid):
        object_id = self.next_object_id
        self.objects[object_id] = centroid
        self.missed[object_id] = 0
        self.next_object_id += 1
        return object_id

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.missed[object_id]

    def update(self, boxes):
        """
        boxes: list of (top, right, bottom, left) tuples detected this frame.

        Returns: a dict mapping object_id -> index into `boxes`, for every
        detection that was matched to an existing tracked face or newly
        registered as one this frame. Use the returned index to look up
        that same detection's box (and its corresponding face encoding,
        since face_recognition.face_encodings() returns encodings in the
        same order as the boxes list you gave it).
        """
        if len(boxes) == 0:
            # Nobody detected this frame — age out anyone we're still tracking.
            for object_id in list(self.missed.keys()):
                self.missed[object_id] += 1
                if self.missed[object_id] > self.max_missed_frames:
                    self.deregister(object_id)
            return {}

        input_centroids = [self.box_to_centroid(b) for b in boxes]

        if len(self.objects) == 0:
            # Nothing tracked yet — every detection this frame is a new face.
            result = {}
            for idx, centroid in enumerate(input_centroids):
                object_id = self.register(centroid)
                result[object_id] = idx
            return result

        object_ids = list(self.objects.keys())
        object_centroids = list(self.objects.values())

        # Distance from every existing tracked centroid to every new detection.
        num_existing = len(object_centroids)
        num_new = len(input_centroids)
        distance_matrix = np.zeros((num_existing, num_new))
        for i, existing_centroid in enumerate(object_centroids):
            for j, new_centroid in enumerate(input_centroids):
                distance_matrix[i, j] = np.linalg.norm(
                    np.array(existing_centroid) - np.array(new_centroid)
                )

        # Greedily pair up the closest matches first.
        rows = distance_matrix.min(axis=1).argsort()
        cols = distance_matrix.argmin(axis=1)[rows]

        used_rows, used_cols = set(), set()
        result = {}

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue
            if distance_matrix[row, col] > self.max_distance:
                continue  # closest match is still too far — not the same face
            object_id = object_ids[row]
            self.objects[object_id] = input_centroids[col]
            self.missed[object_id] = 0
            result[object_id] = col
            used_rows.add(row)
            used_cols.add(col)

        unused_rows = set(range(num_existing)) - used_rows
        unused_cols = set(range(num_new)) - used_cols

        # Existing faces not matched this frame — they may have turned away
        # or been briefly occluded. Give them a few frames' grace period.
        for row in unused_rows:
            object_id = object_ids[row]
            self.missed[object_id] += 1
            if self.missed[object_id] > self.max_missed_frames:
                self.deregister(object_id)

        # Detections not matched to any existing face — brand new people.
        for col in unused_cols:
            object_id = self.register(input_centroids[col])
            result[object_id] = col

        return result
