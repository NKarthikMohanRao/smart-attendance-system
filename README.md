# Smart Attendance System (Face Recognition + Liveness + Anomaly Detection)

## What it does
- Detects and recognizes registered employees' faces via webcam (`face_recognition` / dlib embeddings).
- Requires a **live blink** (Eye Aspect Ratio over consecutive frames) plus a **texture/sharpness check**
  before trusting a face — a static photo held up to the camera won't pass either check.
- On a match: shows the employee's name, code, department, and event (IN/OUT) as an on-screen
  banner for a few seconds, and logs it to SQLite.
- On a live-but-unrecognized face: shows "NOT AN EMPLOYEE", saves a snapshot, and logs the event.
- `anomaly_detection.py` scans the logged history for unusual check-in times, suspiciously rapid
  repeat punches, and marginal-confidence matches worth a human review.

## Architecture & Workflow (Roadmap)
The system is divided into a **React Frontend** and a **Flask Backend**, working together to process attendance securely and efficiently.

1. **Frontend (React + Vite)**: 
   - Provides a modern dashboard for HR to view analytics, reports, and register new employees.
   - Features a **Kiosk Mode** where a tablet or computer can be placed at an entrance. The kiosk captures webcam frames directly in the browser.
2. **Backend (Flask API)**:
   - Receives video frames from the frontend via REST API (`/api/kiosk`).
   - Uses OpenCV and `face_recognition` to generate 128-d face encodings.
   - Performs liveness checks (like Blink Detection via Eye Aspect Ratio).
   - Validates matches against a local SQLite database (`attendance.db`).
   - Returns success or failure status back to the React UI in real-time.

### Step-by-Step User Workflow
1. **Employee Registration**: The HR Admin navigates to the Registration page on the frontend, enters the employee's details, and captures their face. The backend calculates the 128-d facial encoding and stores it securely.
2. **Kiosk Check-In**: An employee walks up to the Attendance Kiosk. The frontend continuously streams webcam snapshots to the backend.
3. **Face Detection & Liveness Check**: The backend detects the face and runs liveness checks (e.g., verifying natural blinking using Eye Aspect Ratio and checking texture sharpness) to prevent spoofing with photos or videos.
4. **Identification & Logging**: The backend matches the live face encoding against the database. If a match is found, their IN/OUT time is recorded in the SQLite database, and the UI displays a success confirmation.
5. **Analytics & Anomalies**: HR can view comprehensive dashboards on the frontend. Additionally, machine learning models (Isolation Forest) flag unusual attendance patterns (e.g., suspiciously rapid repeat punches or odd hours) for manual review.

## Setup
**1. Backend (Python/Flask):**
```bash
pip install -r requirements.txt
```
*(Note: `face_recognition` depends on `dlib`, which compiles from source. You'll usually need `cmake` and a C++ toolchain installed first.)*

**2. Frontend (React/Vite):**
```bash
cd frontend
npm install
```

## Usage
**1. Run the Backend API:**
```bash
python attendance_tracking_app.py
```
*The Flask server will start on `http://127.0.0.1:5000`.*

**2. Run the React Frontend:**
```bash
cd frontend
npm run dev
```
*Access the UI dashboard at `http://localhost:5173`. From here, you can register new employees, view analytics, and run the Kiosk mode for live attendance tracking.*

**3. (Optional) Run the legacy CLI attendance tracker:**
```bash
python attendance_system.py
```

**4. Review anomalies (Machine Learning):**
```bash
python anomaly_detection.py
```

## Tuning
All thresholds live in `config.py`:
- `KNOWN_FACES_TOLERANCE` — lower = stricter identity match, fewer false accepts, more false rejects.
- `BLINK_EAR_THRESHOLD` / `BLINK_CONSEC_FRAMES` — how "closed" an eye must look, and for how long.
- `TEXTURE_SCORE_MIN` — minimum sharpness/color score to accept a frame as live.

Run a short test with your actual webcam and lighting, print the raw `texture_liveness_score`
values for a real face vs. a printed photo of the same person, and set the threshold between them.

## Facial Feature Engineering
When a face is captured, the system performs several layers of feature extraction before identifying the person:
1. **Face Detection (HOG):** OpenCV and `dlib` use a Histogram of Oriented Gradients (HOG) model to locate the bounding box of the face within the frame. It looks for light/dark pixel gradients that outline human facial structures.
2. **68-Point Facial Landmarks:** Once the face is found, the system extracts 68 specific (X, Y) coordinates around the eyes, nose, mouth, and jawline. 
3. **Blink Detection (Eye Aspect Ratio):** Using the 68 landmarks, it measures the distance between the eyelids (the Eye Aspect Ratio or EAR). If the EAR drops below a threshold and then rises rapidly, it registers as a "blink", passing the first liveness test.
4. **128-Dimensional Face Encodings:** For actual identity recognition, the system passes the cropped face through a pre-trained deep neural network (ResNet). This network outputs a 128-dimensional array (an embedding/encoding). This array captures the unique geometrical and textural ratios of the person's face. The system calculates the Euclidean distance between this live 128-d array and the known 128-d arrays in the database to confirm the identity.

## How OpenCV and the React Kiosk Work Together
The **Kiosk** allows any tablet or computer with a webcam to act as an attendance machine using just a web browser.
1. **Webcam Capture (Frontend):** The React frontend requests webcam access via the browser's `navigator.mediaDevices.getUserMedia()`. It captures frames periodically using an HTML5 `<canvas>`.
2. **Data Transmission:** The frame is converted to a base64 JPEG string and sent over HTTP via a `POST` request to the Flask backend's `/api/kiosk` endpoint.
3. **OpenCV Processing (Backend):** 
   - The Flask backend decodes the base64 string back into a NumPy image array.
   - `cv2.cvtColor` is used to convert the image from BGR to RGB (required by `face_recognition`).
   - OpenCV applies the HOG face detector and passes the cropped faces to the neural network for encoding.
   - OpenCV also runs a Laplacian variance filter (`cv2.Laplacian`) to measure image sharpness/texture to ensure the user isn't holding up a blurry printed photo (Liveness Texture Check).
4. **Real-time Feedback:** If OpenCV validates the face and liveness, Flask logs the attendance and responds with a success payload. The React Kiosk instantly flashes a green success screen for the employee.

## Honest limitations — read before relying on this for security
This is a solid learning/prototype-grade anti-spoofing setup, but it is **not a certified liveness
system**:
- Blink + texture checks can be defeated by a **video replay** of the person blinking (e.g. playing
  a clip on a phone/tablet), since that also "blinks" and has decent sharpness.
- Multi-face tracking here uses simple frame-position indexing, which is fine for one person at a
  time but can mix up blink-history between people if several faces move around simultaneously —
  swap in a proper object tracker (e.g. centroid tracking with a Kalman filter) for that scenario.
- The texture-score divisor is tuned loosely and camera-dependent; recalibrate for your hardware.
- For a production/enterprise deployment where false attendance has real financial consequences,
  pair this with an IR or depth camera (structural liveness that a 2D photo/video literally cannot
  fake) or a licensed liveness-detection SDK, rather than relying on webcam heuristics alone.

## Detailed File Uses & Directory Structure
- **`attendance_tracking_app.py`**: The core Flask API server. It handles HTTP requests from the React frontend, coordinates face decoding, interacts with the database, and serves analytics data.
- **`frontend/`**: Contains the React + Vite frontend application. This includes the HR dashboards (`EmployeeAnalytics.tsx`, `HRAnalytics.tsx`), the `Register.tsx` screen, and the `Kiosk.tsx` live attendance interface.
- **`database.py`**: Manages the SQLite connection and schemas. Contains all helper functions to insert/query `employees`, `attendance_log`, and `unknown_events`.
- **`liveness.py`**: Contains the logic to prevent spoofing. It uses Eye Aspect Ratio (EAR) for blink detection and OpenCV's Laplacian variance to calculate a texture/sharpness score to detect printed photos.
- **`anomaly_detection.py`**: A machine learning script utilizing an Isolation Forest model to scan the attendance logs and flag suspicious patterns (like rapid repeat punches or odd check-in hours) for HR review.
- **`attendance_system.py`**: The legacy standalone OpenCV Python script. It opens a native desktop window to stream the webcam and perform attendance (useful if you aren't using the React web frontend).
- **`register_faces.py`**: A CLI utility to quickly enroll new employees from the terminal by capturing their face and computing their 128-d encoding.
- **`config.py`**: The central configuration file holding tunable hyperparameters (e.g., face match tolerance, EAR blink thresholds, minimum texture score).
