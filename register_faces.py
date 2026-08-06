"""
Enroll a new employee: captures several face-encoding samples from the
webcam and stores their average encoding in the database.

Usage:
    python register_faces.py --code E001 --name "Karthik" --dept "Engineering" --designation "Analyst"
"""

import argparse
import cv2
import face_recognition
import numpy as np

import database
import config


def register(emp_code, name, department, designation, num_samples=15):
    database.init_db()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam.")
        return

    encodings_collected = []
    print("Look at the camera. Press 'c' to capture a sample (only when exactly")
    print("one face is detected), or 'q' to stop early.")

    while len(encodings_collected) < num_samples:
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, model="hog")
        display = frame.copy()

        for (top, right, bottom, left) in locations:
            cv2.rectangle(display, (left, top), (right, bottom), (0, 255, 0), 2)

        cv2.putText(display, f"Samples: {len(encodings_collected)}/{num_samples}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow("Register Face - 'c' to capture, 'q' to quit", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('c') and len(locations) == 1:
            encs = face_recognition.face_encodings(rgb, locations)
            if encs:
                encodings_collected.append(encs[0])
                print(f"Captured sample {len(encodings_collected)}/{num_samples}")
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if not encodings_collected:
        print("No samples captured — registration aborted.")
        return

    mean_encoding = np.mean(encodings_collected, axis=0)
    database.add_employee(emp_code, name, department, designation, mean_encoding)
    print(f"Registered '{name}' ({emp_code}) using {len(encodings_collected)} samples.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True, help="Unique employee code / ID")
    parser.add_argument("--name", required=True)
    parser.add_argument("--dept", default="")
    parser.add_argument("--designation", default="")
    parser.add_argument("--samples", type=int, default=15)
    args = parser.parse_args()
    register(args.code, args.name, args.dept, args.designation, args.samples)
