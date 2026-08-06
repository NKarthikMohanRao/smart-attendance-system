"""
Run this after some attendance history has built up:
    python anomaly_detection.py

Flags:
  1. Unusual check-in times per employee (Isolation Forest on hour + day-of-week)
  2. Rapid repeat punches from the same person (< 60s apart) — usually a
     detection glitch or a duplicate trigger rather than a genuine second entry
  3. Low-confidence matches that passed the tolerance cutoff only marginally
     and are worth a human glance
"""

import sqlite3

import pandas as pd
from sklearn.ensemble import IsolationForest

import config


def load_logs():
    conn = sqlite3.connect(config.DB_PATH)
    df = pd.read_sql_query("SELECT * FROM attendance_log", conn)
    conn.close()
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60.0
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    return df


def detect_time_anomalies(df, contamination=0.1):
    results = []
    for emp_code, group in df[df.event_type == "IN"].groupby("emp_code"):
        if len(group) < 5:
            continue  # not enough history yet to model "normal" for this person
        model = IsolationForest(contamination=contamination, random_state=42)
        preds = model.fit_predict(group[["hour", "dayofweek"]].values)
        flagged = group.copy()
        flagged["anomaly"] = preds == -1
        results.append(flagged[flagged.anomaly])
    return pd.concat(results) if results else pd.DataFrame()


def detect_rapid_repeat_punches(df, seconds_threshold=60):
    flagged = []
    for emp_code, group in df.groupby("emp_code"):
        group = group.sort_values("timestamp")
        diffs = group["timestamp"].diff().dt.total_seconds()
        flagged.append(group[diffs < seconds_threshold])
    return pd.concat(flagged) if flagged else pd.DataFrame()


def detect_low_confidence_matches(df, threshold=0.55):
    return df[df.match_confidence < threshold]


def run_anomaly_report():
    df = load_logs()
    if df.empty:
        print("No attendance logs yet.")
        return

    time_anomalies = detect_time_anomalies(df)
    repeat_anomalies = detect_rapid_repeat_punches(df)
    low_conf = detect_low_confidence_matches(df)

    print(f"\nUnusual check-in times: {len(time_anomalies)}")
    if not time_anomalies.empty:
        print(time_anomalies[["emp_code", "name", "timestamp"]].to_string(index=False))

    print(f"\nRapid repeat punches (<60s apart): {len(repeat_anomalies)}")
    if not repeat_anomalies.empty:
        print(repeat_anomalies[["emp_code", "name", "timestamp"]].to_string(index=False))

    print(f"\nLow-confidence matches (worth a review): {len(low_conf)}")
    if not low_conf.empty:
        print(low_conf[["emp_code", "name", "timestamp", "match_confidence"]].to_string(index=False))


if __name__ == "__main__":
    run_anomaly_report()
