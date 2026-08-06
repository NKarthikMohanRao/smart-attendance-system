"""
Main attendance loop: detect faces, require a confirmed blink + texture
liveness pass before trusting the frame, match against registered
employees, log IN/OUT, and show a brief on-screen details banner.
Unrecognized live faces are shown as "NOT AN EMPLOYEE" and snapshotted.
"""

import os
import time

import cv2
import face_recognition
import numpy as np

import config
import database
from liveness import get_ear_for_face, texture_liveness_score, model_based_liveness_score, BlinkTracker
from flicker_detection import FlickerTracker
from cloud_liveness import NullCloudProvider, GenericCloudProvider
from tracker import CentroidTracker


def run():
    database.init_db()
    employees = database.load_all_employees()
    if not employees:
        print("No employees registered yet — run register_faces.py first.")

    known_encodings = [e["encoding"] for e in employees]
    known_meta = employees

    os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam.")
        return

    face_tracker = CentroidTracker(max_distance=75, max_missed_frames=15)
    blink_trackers = {}      # tracked object_id -> BlinkTracker (persists across frames)
    flicker_trackers = {}    # tracked object_id -> FlickerTracker (persists across frames)

    if os.environ.get("CLOUD_LIVENESS_ENDPOINT") and os.environ.get("CLOUD_LIVENESS_API_KEY"):
        cloud_provider = GenericCloudProvider()
    else:
        cloud_provider = NullCloudProvider()

    last_seen_display = {}   # emp_code -> (expiry_ts, info dict) for the banner
    last_logged_time = {}    # emp_code -> last log time, for the cooldown
    frame_count = 0

    print("Smart Attendance System running. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1

        # Detect on a downscaled frame for speed, then scale boxes back up.
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locations_small = face_recognition.face_locations(rgb_small, model="hog")
        locations = [(t * 2, r * 2, b * 2, l * 2) for (t, r, b, l) in locations_small]

        rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_full, locations)

        # Match this frame's detections to persistent identities by centroid
        # position, instead of by list position — this is what lets each
        # person keep their own blink history even when several people move
        # around in front of the camera at once.
        tracked = face_tracker.update(locations)

        # Drop blink trackers for any identity the CentroidTracker has aged
        # out (person left the frame for too long), so memory doesn't grow
        # forever over a long-running session.
        active_ids = set(face_tracker.objects.keys())
        for stale_id in list(blink_trackers.keys()):
            if stale_id not in active_ids:
                del blink_trackers[stale_id]
        for stale_id in list(flicker_trackers.keys()):
            if stale_id not in active_ids:
                del flicker_trackers[stale_id]

        for object_id, idx in tracked.items():
            box = locations[idx]
            face_encoding = encodings[idx]
            top, right, bottom, left = box

            # object_id is now a stable identity for this specific person,
            # persisted by the CentroidTracker across frames.
            blink_tracker = blink_trackers.setdefault(object_id, BlinkTracker())
            flicker_tracker = flicker_trackers.setdefault(object_id, FlickerTracker())

            ear = get_ear_for_face(rgb_full, box)
            blinked = blink_tracker.update(ear)

            face_crop = frame[max(top, 0):bottom, max(left, 0):right]
            looks_like_screen = flicker_tracker.update(face_crop)
            texture_score = texture_liveness_score(face_crop)
            model_score = model_based_liveness_score(face_crop)
            cloud_result = cloud_provider.verify(face_crop)

            # Evaluate each liveness signal
            blink_pass = blinked
            flicker_pass = not looks_like_screen
            model_pass = (model_score > config.MODEL_LIVENESS_THRESHOLD) or (texture_score > config.TEXTURE_SCORE_MIN)
            cloud_pass = (cloud_result.get("is_live") is True or cloud_result.get("is_live") is None)

            is_live = blink_pass and flicker_pass and model_pass and cloud_pass
            color = (0, 255, 0) if is_live else (0, 165, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            if not is_live:
                failing = []
                if not blink_pass:
                    failing.append("blink")
                if not flicker_pass:
                    failing.append("flicker")
                if not model_pass:
                    failing.append("model")
                if not cloud_pass:
                    failing.append("cloud")
                fail_str = "/".join(failing) if failing else "check"
                cv2.putText(frame, f"Verifying liveness ({fail_str})...", (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                continue

            if known_encodings:
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                best_idx = int(np.argmin(distances))
                best_distance = float(distances[best_idx])
            else:
                best_idx, best_distance = -1, 1.0

            if best_idx >= 0 and best_distance <= config.KNOWN_FACES_TOLERANCE:
                emp = known_meta[best_idx]
                confidence = 1.0 - best_distance
                now = time.time()

                cooldown_ok = (
                    emp["emp_code"] not in last_logged_time
                    or now - last_logged_time[emp["emp_code"]] > config.DUPLICATE_PUNCH_COOLDOWN_SECONDS
                )

                if cooldown_ok:
                    last_row = database.last_event_for(emp["emp_code"])
                    next_event = "OUT" if last_row and last_row["event_type"] == "IN" else "IN"

                    database.log_attendance(
                        emp["emp_code"], emp["name"], next_event,
                        liveness_score=max(model_score, texture_score), match_confidence=confidence
                    )
                    last_logged_time[emp["emp_code"]] = now
                    last_seen_display[emp["emp_code"]] = (
                        now + config.DISPLAY_SECONDS,
                        {
                            "name": emp["name"], "code": emp["emp_code"],
                            "dept": emp["department"], "event": next_event,
                            "confidence": confidence,
                        },
                    )

                cv2.putText(frame, emp["name"], (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "NOT AN EMPLOYEE", (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
                if frame_count % 30 == 0 and face_crop.size:
                    snap_path = os.path.join(config.SNAPSHOT_DIR, f"unknown_{int(time.time())}.jpg")
                    cv2.imwrite(snap_path, face_crop)
                    database.log_unknown(snap_path)

        # Draw the "employee details" banner(s) for any recent match still in its display window.
        now = time.time()
        y_offset = 30
        for code in list(last_seen_display.keys()):
            expiry, info = last_seen_display[code]
            if now > expiry:
                del last_seen_display[code]
                continue
            banner = (f"{info['name']} | {info['code']} | {info['dept']} | "
                      f"{info['event']} | {info['confidence'] * 100:.0f}%")
            cv2.rectangle(frame, (0, y_offset - 25), (frame.shape[1], y_offset + 10), (50, 50, 50), -1)
            cv2.putText(frame, banner, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 40

        cv2.imshow("Smart Attendance System", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
