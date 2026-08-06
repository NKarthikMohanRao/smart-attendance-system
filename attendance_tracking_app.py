#!/usr/bin/env python3
"""
attendance_tracking_app.py — Lightweight Standalone Web Dashboard for Smart Attendance System
Reads attendance.db and provides reporting, shift tracking, overtime, under-shift, and missed-punch alerts.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, url_for, jsonify
from flask_cors import CORS
import base64
import numpy as np
import cv2
import face_recognition
import time
import config
import database
from liveness import texture_liveness_score, model_based_liveness_score
from ml_pipeline import PredictiveHRAnalytics

app = Flask(__name__)
CORS(app)


def get_db_connection(db_path=None):
    """Returns a SQLite connection to attendance.db with row_factory=sqlite3.Row."""
    path = db_path or config.DB_PATH
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def is_db_empty(db_path=None):
    """Checks if the database is missing or has no registered employees."""
    conn = get_db_connection(db_path)
    if not conn:
        return True
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM sqlite_master WHERE type='table' AND name='employees'")
        if cur.fetchone()["cnt"] == 0:
            return True
        cur.execute("SELECT COUNT(*) as cnt FROM employees")
        return cur.fetchone()["cnt"] == 0
    except Exception:
        return True
    finally:
        conn.close()


def parse_iso_datetime(ts_str):
    """Parses SQLite timestamp strings into datetime objects."""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(ts_str[:26], fmt)
            except ValueError:
                pass
    return None


def get_date_range(start_date_str, end_date_str):
    """Returns a list of YYYY-MM-DD date strings from start_date_str to end_date_str inclusive."""
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    except Exception:
        today = datetime.now().date()
        start_dt = today - timedelta(days=6)
        end_dt = today
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt
    days = []
    curr = start_dt
    while curr <= end_dt:
        days.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return days


def get_default_dates(db_path=None):
    """
    Returns (start_date, end_date) defaults. If the database has attendance logs,
    end_date defaults to the latest logged day (or today), and start_date to 6 days prior.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    start_str = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
    conn = get_db_connection(db_path)
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT MAX(timestamp) as max_ts, MIN(timestamp) as min_ts FROM attendance_log")
            row = cur.fetchone()
            if row and row["max_ts"]:
                latest_dt = parse_iso_datetime(row["max_ts"])
                if latest_dt:
                    latest_str = latest_dt.strftime("%Y-%m-%d")
                    if latest_str > today_str:
                        today_str = latest_str
                    start_str = (datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=6)).strftime("%Y-%m-%d")
        except Exception:
            pass
        finally:
            conn.close()
    return start_str, today_str


def load_employees(db_path=None):
    """Loads all employees from the employees table."""
    conn = get_db_connection(db_path)
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT emp_code, name, department, designation FROM employees ORDER BY name")
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def load_attendance_for_day(emp_code, day_str, db_path=None):
    """Loads all attendance_log rows for an employee on a specific date (YYYY-MM-DD)."""
    conn = get_db_connection(db_path)
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT * FROM attendance_log 
               WHERE emp_code = ? AND timestamp LIKE ? 
               ORDER BY timestamp ASC""",
            (emp_code, f"{day_str}%")
        )
        return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def compute_daily_attendance(emp, day_str, events):
    """
    Computes per employee, per calendar day metrics from paired IN/OUT rows:
    1. Login time (first IN that day) and logout time (last OUT that day).
    2. Total hours worked (sum of all IN->OUT pair durations that day).
    3. Break time (total gap between an OUT and the next IN, same day).
    4. Overtime (hours beyond STANDARD_SHIFT_HOURS).
    5. Under-shift alert (total hours worked below MIN_SHIFT_HOURS, only for days with at least 1 punch; 0 punches = absent).
    6. Missed punches (an odd number of events that day for that employee, meaning punches can't be cleanly paired).
    """
    emp_code = emp.get("emp_code", "")
    name = emp.get("name", "")
    department = emp.get("department", "")

    login_time = None
    logout_time = None

    # Find login time (first IN)
    for ev in events:
        if ev["event_type"].upper() == "IN":
            dt = parse_iso_datetime(ev["timestamp"])
            if dt:
                login_time = dt.strftime("%H:%M:%S")
            break

    # Find logout time (last OUT)
    for ev in reversed(events):
        if ev["event_type"].upper() == "OUT":
            dt = parse_iso_datetime(ev["timestamp"])
            if dt:
                logout_time = dt.strftime("%H:%M:%S")
            break

    hours_worked = 0.0
    break_time = 0.0
    n = len(events)
    is_absent = (n == 0)
    is_missed_punch = False

    # Check odd number of punches or unclean pairs
    if n > 0:
        if n % 2 != 0:
            is_missed_punch = True
        else:
            for idx in range(0, n, 2):
                if events[idx]["event_type"].upper() != "IN" or events[idx + 1]["event_type"].upper() != "OUT":
                    is_missed_punch = True
                    break

    # Pair IN -> OUT for hours worked, and OUT -> next IN for break time
    i = 0
    while i < n:
        if events[i]["event_type"].upper() == "IN":
            if i + 1 < n and events[i + 1]["event_type"].upper() == "OUT":
                in_dt = parse_iso_datetime(events[i]["timestamp"])
                out_dt = parse_iso_datetime(events[i + 1]["timestamp"])
                if in_dt and out_dt and out_dt > in_dt:
                    duration = (out_dt - in_dt).total_seconds() / 3600.0
                    hours_worked += duration

                # Check break to next IN
                if i + 2 < n and events[i + 2]["event_type"].upper() == "IN":
                    next_in_dt = parse_iso_datetime(events[i + 2]["timestamp"])
                    if out_dt and next_in_dt and next_in_dt > out_dt:
                        gap = (next_in_dt - out_dt).total_seconds() / 3600.0
                        break_time += gap

                i += 2
                continue
        i += 1

    standard_shift = getattr(config, "STANDARD_SHIFT_HOURS", 9.0)
    min_shift = getattr(config, "MIN_SHIFT_HOURS", 8.0)

    overtime = max(0.0, hours_worked - standard_shift)
    is_under_shift = (not is_absent and hours_worked < min_shift)
    has_overtime = (overtime > 0)

    # Determine status flags
    flags = []
    if is_absent:
        flags.append("Absent")
    if is_missed_punch:
        flags.append("Missed Punch")
    if is_under_shift:
        flags.append("Under-Shift")
    if has_overtime:
        flags.append("Overtime")
    if not flags:
        flags.append("Normal")

    return {
        "date": day_str,
        "emp_code": emp_code,
        "name": name,
        "department": department,
        "login_time": login_time,
        "logout_time": logout_time,
        "hours_worked": hours_worked,
        "break_time": break_time,
        "overtime": overtime,
        "is_absent": is_absent,
        "is_under_shift": is_under_shift,
        "is_missed_punch": is_missed_punch,
        "has_overtime": has_overtime,
        "flags": flags,
    }


# ==============================================================================
# FLASK WEB DASHBOARD ROUTES
# ==============================================================================

@app.route("/api/summary")
def home():
    """Dashboard Home: summary cards, overtime chart, and compliance overview."""
    empty = is_db_empty()
    default_start, default_end = get_default_dates()
    start_date = request.args.get("start_date", default_start)
    end_date = request.args.get("end_date", default_end)

    if empty:
        return jsonify({
            "is_empty_db": True,
            "start_date": start_date,
            "end_date": end_date
        })

    employees = load_employees()
    days = get_date_range(start_date, end_date)

    total_employees = len(employees)
    total_overtime_hours = 0.0
    count_undershift_days = 0
    count_missed_punch_days = 0
    count_absent_days = 0
    count_normal_days = 0
    count_overtime_days = 0

    for emp in employees:
        for day_str in days:
            events = load_attendance_for_day(emp["emp_code"], day_str)
            rec = compute_daily_attendance(emp, day_str, events)
            total_overtime_hours += rec["overtime"]
            if rec["is_under_shift"]:
                count_undershift_days += 1
            if rec["is_missed_punch"]:
                count_missed_punch_days += 1
            if rec["is_absent"]:
                count_absent_days += 1
            if rec["has_overtime"]:
                count_overtime_days += 1
            if "Normal" in rec["flags"]:
                count_normal_days += 1

    return jsonify({
        "is_empty_db": False,
        "start_date": start_date,
        "end_date": end_date,
        "total_employees": total_employees,
        "total_overtime_hours": total_overtime_hours,
        "count_undershift_days": count_undershift_days,
        "count_missed_punch_days": count_missed_punch_days,
        "count_absent_days": count_absent_days,
        "count_normal_days": count_normal_days,
        "count_overtime_days": count_overtime_days,
        "standard_shift": getattr(config, "STANDARD_SHIFT_HOURS", 9.0),
        "min_shift": getattr(config, "MIN_SHIFT_HOURS", 8.0)
    })


@app.route("/api/employee")
def employee_detail():
    """Employee Detail Page: day-by-day table for a selected employee and date range."""
    empty = is_db_empty()
    default_start, default_end = get_default_dates()
    start_date = request.args.get("start_date", default_start)
    end_date = request.args.get("end_date", default_end)

    if empty:
        return jsonify({
            "is_empty_db": True,
            "start_date": start_date,
            "end_date": end_date
        })

    employees = load_employees()
    emp_code = request.args.get("emp_code")
    selected_emp = None
    if emp_code:
        for emp in employees:
            if emp["emp_code"] == emp_code:
                selected_emp = emp
                break
    if not selected_emp and employees:
        selected_emp = employees[0]

    days = get_date_range(start_date, end_date)
    daily_records = []
    total_emp_hours = 0.0
    total_emp_overtime = 0.0
    count_emp_undershift = 0
    count_emp_missed = 0

    if selected_emp:
        for day_str in days:
            events = load_attendance_for_day(selected_emp["emp_code"], day_str)
            rec = compute_daily_attendance(selected_emp, day_str, events)
            daily_records.append(rec)
            total_emp_hours += rec["hours_worked"]
            total_emp_overtime += rec["overtime"]
            if rec["is_under_shift"]:
                count_emp_undershift += 1
            if rec["is_missed_punch"]:
                count_emp_missed += 1

    return jsonify({
        "is_empty_db": False,
        "employees": employees,
        "selected_emp": selected_emp,
        "daily_records": daily_records,
        "start_date": start_date,
        "end_date": end_date,
        "total_emp_hours": total_emp_hours,
        "total_emp_overtime": total_emp_overtime,
        "count_emp_undershift": count_emp_undershift,
        "count_emp_missed": count_emp_missed,
        "min_shift": getattr(config, "MIN_SHIFT_HOURS", 8.0)
    })


@app.route("/api/report")
def report():
    """All-Employees Report Table: one row per employee per day across selected date range."""
    empty = is_db_empty()
    default_start, default_end = get_default_dates()
    start_date = request.args.get("start_date", default_start)
    end_date = request.args.get("end_date", default_end)

    if empty:
        return jsonify({
            "is_empty_db": True,
            "start_date": start_date,
            "end_date": end_date
        })

    employees = load_employees()
    days = get_date_range(start_date, end_date)
    all_records = []

    for day_str in days:
        for emp in employees:
            events = load_attendance_for_day(emp["emp_code"], day_str)
            rec = compute_daily_attendance(emp, day_str, events)
            all_records.append(rec)

    # Sort descending by date by default
    all_records.sort(key=lambda r: (r["date"], r["name"]), reverse=True)

    return jsonify({
        "is_empty_db": False,
        "start_date": start_date,
        "end_date": end_date,
        "all_records": all_records,
        "min_shift": getattr(config, "MIN_SHIFT_HOURS", 8.0)
    })




@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    if not data:
        return {"error": "Invalid payload"}, 400

    emp_code = data.get("emp_code")
    name = data.get("name")
    department = data.get("department", "")
    designation = data.get("designation", "")
    images = data.get("images", [])

    if not emp_code or not name:
        return {"error": "Employee Code and Name are required"}, 400
    if not images:
        return {"error": "No images provided for registration"}, 400

    encodings = []
    for b64_str in images:
        try:
            # Strip the data:image/jpeg;base64, header if present
            if "," in b64_str:
                b64_str = b64_str.split(",")[1]
            
            img_data = base64.b64decode(b64_str)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb, model="hog")
            if len(locations) == 1:
                encs = face_recognition.face_encodings(rgb, locations)
                if encs:
                    encodings.append(encs[0])
        except Exception as e:
            print(f"Error processing image: {e}")
            continue

    if not encodings:
        return {"error": "Could not detect a clear face in the provided images."}, 400

    mean_encoding = np.mean(encodings, axis=0)
    
    try:
        database.add_employee(emp_code, name, department, designation, mean_encoding)
        return {"success": True, "message": f"Successfully registered {name} ({emp_code})."}
    except Exception as e:
        # Most likely unique constraint violation for emp_code
        return {"error": f"Failed to register employee: {str(e)}"}, 500

@app.route("/api/employee/<emp_code>", methods=["DELETE"])
def api_delete_employee(emp_code):
    try:
        database.delete_employee(emp_code)
        return {"success": True, "message": f"Successfully deleted employee {emp_code}."}
    except Exception as e:
        return {"error": str(e)}, 500

# ==============================================================================
# PREDICTIVE HR ANALYTICS ROUTES
# ==============================================================================

@app.route("/api/analytics/dashboard")
def analytics_dashboard():
    analytics_engine = PredictiveHRAnalytics()
    results = analytics_engine.generate_all_analytics()
    if results.get("status") == "error":
        return jsonify(results), 400
    return jsonify(results["hr_dashboard"])

@app.route("/api/analytics/employee/<emp_code>")
def analytics_employee(emp_code):
    analytics_engine = PredictiveHRAnalytics()
    results = analytics_engine.generate_all_analytics()
    if results.get("status") == "error":
        return jsonify(results), 400
        
    emp_data = results["employees"].get(emp_code)
    if not emp_data:
        return jsonify({"error": "Employee analytics not found."}), 404
        
    return jsonify(emp_data)

# Global state for kiosk cooldowns
kiosk_last_logged_time = {}



@app.route("/api/kiosk", methods=["POST"])
def api_kiosk():
    data = request.json
    if not data or not data.get("image"):
        return {"error": "Invalid payload"}, 400

    b64_str = data["image"]
    if "," in b64_str:
        b64_str = b64_str.split(",")[1]

    try:
        img_data = base64.b64decode(b64_str)
        np_arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    except Exception as e:
        return {"error": "Failed to decode image"}, 400

    # Downscale for faster detection
    small = cv2.resize(rgb, (0, 0), fx=0.5, fy=0.5)
    locations_small = face_recognition.face_locations(small, model="hog")
    locations = [(t * 2, r * 2, b * 2, l * 2) for (t, r, b, l) in locations_small]

    if not locations:
        return {"status": "no_face"}

    encodings = face_recognition.face_encodings(rgb, locations)
    
    # Process only the first face found for kiosk mode simplicity
    top, right, bottom, left = locations[0]
    face_encoding = encodings[0]
    
    face_crop = frame[max(top, 0):bottom, max(left, 0):right]
    
    if face_crop.size == 0:
        return {"status": "no_face"}

    # Liveness check
    texture_score = texture_liveness_score(face_crop)
    model_score = model_based_liveness_score(face_crop)
    
    if texture_score <= config.TEXTURE_SCORE_MIN and model_score <= config.MODEL_LIVENESS_THRESHOLD:
        return {"status": "spoof", "message": "Liveness check failed."}

    employees = database.load_all_employees()
    if not employees:
        return {"status": "error", "message": "No registered employees."}

    known_encodings = [e["encoding"] for e in employees]
    distances = face_recognition.face_distance(known_encodings, face_encoding)
    best_idx = int(np.argmin(distances))
    best_distance = float(distances[best_idx])

    if best_distance <= config.KNOWN_FACES_TOLERANCE:
        emp = employees[best_idx]
        confidence = 1.0 - best_distance
        now = time.time()
        emp_code = emp["emp_code"]

        cooldown_ok = (
            emp_code not in kiosk_last_logged_time
            or now - kiosk_last_logged_time[emp_code] > config.DUPLICATE_PUNCH_COOLDOWN_SECONDS
        )

        if cooldown_ok:
            last_row = database.last_event_for(emp_code)
            next_event = "OUT" if last_row and last_row["event_type"] == "IN" else "IN"
            
            # Use the higher liveness score for logging
            final_liveness = max(model_score, texture_score)
            database.log_attendance(emp_code, emp["name"], next_event, final_liveness, confidence)
            kiosk_last_logged_time[emp_code] = now
            
            return {
                "status": "success",
                "name": emp["name"],
                "event": next_event,
                "confidence": round(confidence * 100)
            }
        else:
            # On cooldown, just acknowledge they are recognized but don't log a duplicate
            return {
                "status": "cooldown",
                "name": emp["name"]
            }
    else:
        # Unknown face
        return {"status": "unknown"}

if __name__ == "__main__":
    print("================================================================")
    print("  Smart Attendance Web Dashboard running on http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop.")
    print("================================================================")
    app.run(host="0.0.0.0", port=5000, debug=False)
