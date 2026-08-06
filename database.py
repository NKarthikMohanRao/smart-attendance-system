import sqlite3
import numpy as np
from datetime import datetime
import config


def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            designation TEXT,
            face_encoding BLOB NOT NULL,
            registered_on TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_code TEXT,
            name TEXT,
            event_type TEXT,
            timestamp TEXT NOT NULL,
            liveness_score REAL,
            match_confidence REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS unknown_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            snapshot_path TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_employee(emp_code, name, department, designation, encoding):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO employees
           (emp_code, name, department, designation, face_encoding, registered_on)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (emp_code, name, department, designation,
         np.asarray(encoding, dtype=np.float64).tobytes(),
         datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def load_all_employees():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees")
    rows = cur.fetchall()
    conn.close()
    employees = []
    for r in rows:
        encoding = np.frombuffer(r["face_encoding"], dtype=np.float64)
        employees.append({
            "emp_code": r["emp_code"],
            "name": r["name"],
            "department": r["department"],
            "designation": r["designation"],
            "encoding": encoding,
        })
    return employees


def log_attendance(emp_code, name, event_type, liveness_score, match_confidence):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO attendance_log
           (emp_code, name, event_type, timestamp, liveness_score, match_confidence)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (emp_code, name, event_type, datetime.now().isoformat(),
         liveness_score, match_confidence)
    )
    conn.commit()
    conn.close()


def log_unknown(snapshot_path=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO unknown_events (timestamp, snapshot_path) VALUES (?, ?)",
        (datetime.now().isoformat(), snapshot_path)
    )
    conn.commit()
    conn.close()


def last_event_for(emp_code):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM attendance_log WHERE emp_code=? ORDER BY timestamp DESC LIMIT 1",
        (emp_code,)
    )
    row = cur.fetchone()
    conn.close()
    return row

def delete_employee(emp_code):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM employees WHERE emp_code = ?", (emp_code,))
    cur.execute("DELETE FROM attendance_log WHERE emp_code = ?", (emp_code,))
    conn.commit()
    conn.close()
