#!/usr/bin/env python3
"""
test_dashboard_calculations.py
Creates a throwaway test database, inserts test rows with known hand-calculated values,
and verifies each computed column (hours worked, overtime, under-shift, break, missed punch),
as well as Flask endpoint rendering and empty database fallback.
"""

import os
import sqlite3
import unittest
from datetime import datetime
import attendance_tracking_app as app_module
import config


class TestDashboardCalculations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_db = "test_attendance_throwaway.db"
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)

        conn = sqlite3.connect(cls.test_db)
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

        # 1. EMP001 (Alice) - 9.5 hours worked, 1.0 hr break, 0.5 hr overtime
        cur.execute("INSERT INTO employees VALUES (1, 'EMP001', 'Alice Smith', 'Engineering', 'Lead', X'00', '2026-08-01T00:00:00')")
        cur.execute("INSERT INTO attendance_log VALUES (1, 'EMP001', 'Alice Smith', 'IN',  '2026-08-01T08:00:00', 0.9, 0.99)")
        cur.execute("INSERT INTO attendance_log VALUES (2, 'EMP001', 'Alice Smith', 'OUT', '2026-08-01T12:00:00', 0.9, 0.99)")
        cur.execute("INSERT INTO attendance_log VALUES (3, 'EMP001', 'Alice Smith', 'IN',  '2026-08-01T13:00:00', 0.9, 0.99)")
        cur.execute("INSERT INTO attendance_log VALUES (4, 'EMP001', 'Alice Smith', 'OUT', '2026-08-01T18:30:00', 0.9, 0.99)")

        # 2. EMP002 (Bob) - 7.0 hours worked, 1.0 hr break, 0.0 hr overtime, under-shift=True
        cur.execute("INSERT INTO employees VALUES (2, 'EMP002', 'Bob Jones', 'Sales', 'Rep', X'00', '2026-08-01T00:00:00')")
        cur.execute("INSERT INTO attendance_log VALUES (5, 'EMP002', 'Bob Jones', 'IN',  '2026-08-01T09:00:00', 0.9, 0.99)")
        cur.execute("INSERT INTO attendance_log VALUES (6, 'EMP002', 'Bob Jones', 'OUT', '2026-08-01T13:00:00', 0.9, 0.99)")
        cur.execute("INSERT INTO attendance_log VALUES (7, 'EMP002', 'Bob Jones', 'IN',  '2026-08-01T14:00:00', 0.9, 0.99)")
        cur.execute("INSERT INTO attendance_log VALUES (8, 'EMP002', 'Bob Jones', 'OUT', '2026-08-01T17:00:00', 0.9, 0.99)")

        # 3. EMP003 (Charlie) - 3 punches (IN, OUT, IN) -> missed_punch=True
        cur.execute("INSERT INTO employees VALUES (3, 'EMP003', 'Charlie Brown', 'Support', 'Agent', X'00', '2026-08-01T00:00:00')")
        cur.execute("INSERT INTO attendance_log VALUES (9,  'EMP003', 'Charlie Brown', 'IN',  '2026-08-01T09:00:00', 0.9, 0.99)")
        cur.execute("INSERT INTO attendance_log VALUES (10, 'EMP003', 'Charlie Brown', 'OUT', '2026-08-01T12:00:00', 0.9, 0.99)")
        cur.execute("INSERT INTO attendance_log VALUES (11, 'EMP003', 'Charlie Brown', 'IN',  '2026-08-01T13:00:00', 0.9, 0.99)")

        # 4. EMP004 (Diana) - 0 punches -> absent=True, under-shift=False
        cur.execute("INSERT INTO employees VALUES (4, 'EMP004', 'Diana Prince', 'HR', 'Manager', X'00', '2026-08-01T00:00:00')")

        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db):
            try:
                os.remove(cls.test_db)
            except Exception:
                pass

    def test_01_alice_overtime_and_break(self):
        emp = {"emp_code": "EMP001", "name": "Alice Smith", "department": "Engineering"}
        events = app_module.load_attendance_for_day("EMP001", "2026-08-01", db_path=self.test_db)
        rec = app_module.compute_daily_attendance(emp, "2026-08-01", events)

        self.assertEqual(rec["login_time"], "08:00:00")
        self.assertEqual(rec["logout_time"], "18:30:00")
        self.assertAlmostEqual(rec["hours_worked"], 9.5, places=2)
        self.assertAlmostEqual(rec["break_time"], 1.0, places=2)
        self.assertAlmostEqual(rec["overtime"], 0.5, places=2)
        self.assertFalse(rec["is_under_shift"])
        self.assertFalse(rec["is_missed_punch"])
        self.assertFalse(rec["is_absent"])
        self.assertIn("Overtime", rec["flags"])

    def test_02_bob_undershift(self):
        emp = {"emp_code": "EMP002", "name": "Bob Jones", "department": "Sales"}
        events = app_module.load_attendance_for_day("EMP002", "2026-08-01", db_path=self.test_db)
        rec = app_module.compute_daily_attendance(emp, "2026-08-01", events)

        self.assertEqual(rec["login_time"], "09:00:00")
        self.assertEqual(rec["logout_time"], "17:00:00")
        self.assertAlmostEqual(rec["hours_worked"], 7.0, places=2)
        self.assertAlmostEqual(rec["break_time"], 1.0, places=2)
        self.assertAlmostEqual(rec["overtime"], 0.0, places=2)
        self.assertTrue(rec["is_under_shift"])
        self.assertFalse(rec["is_missed_punch"])
        self.assertFalse(rec["is_absent"])
        self.assertIn("Under-Shift", rec["flags"])

    def test_03_charlie_missed_punch(self):
        emp = {"emp_code": "EMP003", "name": "Charlie Brown", "department": "Support"}
        events = app_module.load_attendance_for_day("EMP003", "2026-08-01", db_path=self.test_db)
        rec = app_module.compute_daily_attendance(emp, "2026-08-01", events)

        self.assertTrue(rec["is_missed_punch"])
        self.assertAlmostEqual(rec["hours_worked"], 3.0, places=2)
        self.assertIn("Missed Punch", rec["flags"])

    def test_04_diana_absent_not_undershift(self):
        emp = {"emp_code": "EMP004", "name": "Diana Prince", "department": "HR"}
        events = app_module.load_attendance_for_day("EMP004", "2026-08-01", db_path=self.test_db)
        rec = app_module.compute_daily_attendance(emp, "2026-08-01", events)

        self.assertTrue(rec["is_absent"])
        self.assertFalse(rec["is_under_shift"], "Zero punches should be absent, NOT under-shift")
        self.assertFalse(rec["is_missed_punch"])
        self.assertAlmostEqual(rec["hours_worked"], 0.0, places=2)
        self.assertIn("Absent", rec["flags"])

    def test_05_flask_routes_with_data(self):
        original_db = config.DB_PATH
        try:
            config.DB_PATH = self.test_db
            client = app_module.app.test_client()

            r_home = client.get("/?start_date=2026-08-01&end_date=2026-08-01")
            self.assertEqual(r_home.status_code, 200)
            self.assertIn(b"Total Overtime", r_home.data)

            r_emp = client.get("/employee?start_date=2026-08-01&end_date=2026-08-01&emp_code=EMP001")
            self.assertEqual(r_emp.status_code, 200)
            self.assertIn(b"Alice Smith", r_emp.data)

            r_report = client.get("/report?start_date=2026-08-01&end_date=2026-08-01")
            self.assertEqual(r_report.status_code, 200)
            self.assertIn(b"Bob Jones", r_report.data)
        finally:
            config.DB_PATH = original_db

    def test_06_empty_database_fallback(self):
        original_db = config.DB_PATH
        try:
            config.DB_PATH = "non_existent_db.sqlite"
            client = app_module.app.test_client()

            r_home = client.get("/")
            self.assertEqual(r_home.status_code, 200)
            self.assertIn(b"No Attendance Data Yet", r_home.data)

            r_emp = client.get("/employee")
            self.assertEqual(r_emp.status_code, 200)
            self.assertIn(b"No Employee Records Available", r_emp.data)

            r_report = client.get("/report")
            self.assertEqual(r_report.status_code, 200)
            self.assertIn(b"No Report Records Found", r_report.data)
        finally:
            config.DB_PATH = original_db


if __name__ == "__main__":
    unittest.main()
