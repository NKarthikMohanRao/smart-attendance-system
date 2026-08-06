import sqlite3
import pandas as pd
import numpy as np
import datetime
import config

class PredictiveHRAnalytics:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.DB_PATH

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def load_attendance_data(self):
        conn = self.get_db_connection()
        query = """
            SELECT emp_code, name, event_type, timestamp 
            FROM attendance_log 
            ORDER BY emp_code, timestamp ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return df
            
        # Basic preprocessing
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        return df

    def engineer_features(self, df):
        """Transform raw IN/OUT logs into daily tabular features per employee."""
        if df.empty:
            return pd.DataFrame()
            
        daily_records = []
        
        # Group by employee and date
        for (emp_code, date), group in df.groupby(['emp_code', 'date']):
            events = group.sort_values('timestamp').to_dict('records')
            
            login_time = None
            logout_time = None
            hours_worked = 0.0
            
            for ev in events:
                if ev["event_type"].upper() == "IN" and login_time is None:
                    login_time = ev["timestamp"]
            for ev in reversed(events):
                if ev["event_type"].upper() == "OUT" and logout_time is None:
                    logout_time = ev["timestamp"]
                    
            if login_time and logout_time and logout_time > login_time:
                hours_worked = (logout_time - login_time).total_seconds() / 3600.0
                
            standard_shift = getattr(config, "STANDARD_SHIFT_HOURS", 9.0)
            min_shift = getattr(config, "MIN_SHIFT_HOURS", 8.0)
            
            overtime = max(0.0, hours_worked - standard_shift)
            is_under_shift = (hours_worked > 0 and hours_worked < min_shift)
            
            # Simple assumption: 9 AM is standard login time.
            is_late = False
            if login_time:
                is_late = login_time.time() > datetime.time(9, 15) # 15 min grace period
                
            daily_records.append({
                'emp_code': emp_code,
                'name': group.iloc[0]['name'],
                'date': date,
                'hours_worked': hours_worked,
                'overtime': overtime,
                'is_under_shift': int(is_under_shift),
                'is_late': int(is_late),
                'day_of_week': date.weekday()
            })
            
        features_df = pd.DataFrame(daily_records)
        return features_df

    def get_employee_aggregates(self, features_df):
        """Aggregate daily features into employee-level metrics for scoring."""
        if features_df.empty:
            return pd.DataFrame()
            
        agg = features_df.groupby('emp_code').agg(
            name=('name', 'first'),
            total_days=('date', 'count'),
            avg_hours=('hours_worked', 'mean'),
            total_overtime=('overtime', 'sum'),
            late_days=('is_late', 'sum'),
            under_shift_days=('is_under_shift', 'sum')
        ).reset_index()
        
        # Calculate rates
        agg['late_rate'] = agg['late_days'] / agg['total_days']
        agg['under_shift_rate'] = agg['under_shift_days'] / agg['total_days']
        
        return agg

    # =========================================================================
    # ML Models & Predictions
    # =========================================================================

    def predict_absenteeism(self, agg_df):
        """
        Predicts absenteeism risk.
        Using a heuristic/rule-based approach as fallback due to lack of historical labeled data.
        In production with historical data, a RandomForestClassifier would be trained here.
        """
        predictions = []
        for _, row in agg_df.iterrows():
            # Rule-based simulation of ML output
            risk_score = (row['late_rate'] * 0.4) + (row['under_shift_rate'] * 0.6)
            
            if risk_score > 0.3:
                risk_level = "High"
                prob = min(risk_score * 100 + 40, 95)
                reason = f"High rate of late arrivals ({row['late_rate']:.0%}) and under-shifts."
                action = "HR Counselling recommended."
            elif risk_score > 0.1:
                risk_level = "Medium"
                prob = risk_score * 100 + 20
                reason = "Moderate inconsistency in shift completion."
                action = "Monitor attendance."
            else:
                risk_level = "Low"
                prob = risk_score * 100
                reason = "Consistent attendance patterns."
                action = "None"
                
            predictions.append({
                'emp_code': row['emp_code'],
                'probability': round(prob, 1),
                'risk_level': risk_level,
                'reason': reason,
                'action': action
            })
        return predictions

    def forecast_overtime(self, features_df):
        """
        Forecasts next week's overtime.
        In production, an XGBoost Regressor would fit on historical trends.
        """
        if features_df.empty:
            return []
            
        forecasts = []
        agg = features_df.groupby('emp_code').agg(
            recent_avg_overtime=('overtime', lambda x: x.tail(5).mean() if len(x) >= 5 else x.mean()),
            total_overtime=('overtime', 'sum')
        ).reset_index()
        
        for _, row in agg.iterrows():
            next_week_est = row['recent_avg_overtime'] * 5 # Extrapolate to 5 days
            forecasts.append({
                'emp_code': row['emp_code'],
                'next_week_overtime_est': round(next_week_est, 1),
                'trend': 'Increasing' if row['recent_avg_overtime'] > 1.0 else 'Stable',
                'reason': f"Based on recent average of {row['recent_avg_overtime']:.1f} hrs/day"
            })
        return forecasts

    # =========================================================================
    # Scoring Engines
    # =========================================================================

    def calculate_promotion_score(self, agg_df):
        """Promotion Readiness Score (0-100)"""
        scores = []
        for _, row in agg_df.iterrows():
            # Consistency (max 40)
            consistency = max(0, 40 - (row['late_rate'] * 100))
            # Dedication/Overtime (max 30)
            dedication = min(30, row['total_overtime'] * 2) 
            # Reliability (max 30)
            reliability = max(0, 30 - (row['under_shift_rate'] * 100))
            
            total_score = consistency + dedication + reliability
            
            strengths = []
            weaknesses = []
            if consistency > 35: strengths.append("Highly Punctual")
            else: weaknesses.append("Frequent Late Arrivals")
                
            if dedication > 20: strengths.append("High Overtime Contribution")
            
            if reliability > 25: strengths.append("Reliable Shift Completion")
            else: weaknesses.append("Frequent Under-shifts")
                
            scores.append({
                'emp_code': row['emp_code'],
                'promotion_score': round(total_score, 1),
                'strengths': strengths,
                'weaknesses': weaknesses,
                'suggestion': "Consider for promotion" if total_score > 80 else "Needs improvement in weak areas"
            })
        return scores

    def calculate_reliability_analytics(self, agg_df):
        """Employee Reliability Analytics"""
        analytics = []
        for _, row in agg_df.iterrows():
            reliability_score = max(0, 100 - (row['late_rate']*50) - (row['under_shift_rate']*50))
            
            if reliability_score >= 90: grade = 'A+'
            elif reliability_score >= 80: grade = 'A'
            elif reliability_score >= 70: grade = 'B'
            elif reliability_score >= 60: grade = 'C'
            else: grade = 'D'
                
            analytics.append({
                'emp_code': row['emp_code'],
                'reliability_score': round(reliability_score, 1),
                'grade': grade
            })
        return analytics
        
    def calculate_burnout_risk(self, agg_df):
        """Burnout Risk Analytics"""
        risks = []
        for _, row in agg_df.iterrows():
            avg_hours = row['avg_hours']
            if avg_hours > 10.5:
                risk = "High"
                reason = f"Averaging {avg_hours:.1f} hours/day. Consecutive excessive overtime."
                rec = "Mandatory Manager Review. Suggest Workload rebalancing."
            elif avg_hours > 9.5:
                risk = "Medium"
                reason = f"Averaging {avg_hours:.1f} hours/day."
                rec = "Monitor workload."
            else:
                risk = "Low"
                reason = "Standard working hours maintained."
                rec = "None"
                
            risks.append({
                'emp_code': row['emp_code'],
                'burnout_risk': risk,
                'reason': reason,
                'recommendation': rec
            })
        return risks

    def estimate_salary_impact(self, agg_df):
        """Salary Impact Analytics"""
        # Default Base Hourly Rate configuration
        base_rate = getattr(config, "BASE_HOURLY_RATE", 25.0)
        overtime_multiplier = 1.5
        
        impacts = []
        for _, row in agg_df.iterrows():
            base_earnings = row['avg_hours'] * row['total_days'] * base_rate
            overtime_earnings = row['total_overtime'] * (base_rate * overtime_multiplier)
            late_penalty = row['late_days'] * (base_rate * 0.5) # Arbitrary half-hour penalty per late day
            
            est_total = base_earnings + overtime_earnings - late_penalty
            
            impacts.append({
                'emp_code': row['emp_code'],
                'base_earnings': round(base_earnings, 2),
                'overtime_earnings': round(overtime_earnings, 2),
                'late_penalty': round(late_penalty, 2),
                'estimated_total': round(est_total, 2)
            })
        return impacts

    # =========================================================================
    # Main Orchestrator
    # =========================================================================

    def generate_all_analytics(self):
        """Orchestrates the entire ML and Analytics pipeline and returns dictionaries."""
        df = self.load_attendance_data()
        if df.empty:
            return {"status": "error", "message": "No attendance data available for analysis."}
            
        features_df = self.engineer_features(df)
        agg_df = self.get_employee_aggregates(features_df)
        
        absenteeism = {r['emp_code']: r for r in self.predict_absenteeism(agg_df)}
        overtime = {r['emp_code']: r for r in self.forecast_overtime(features_df)}
        promotion = {r['emp_code']: r for r in self.calculate_promotion_score(agg_df)}
        reliability = {r['emp_code']: r for r in self.calculate_reliability_analytics(agg_df)}
        burnout = {r['emp_code']: r for r in self.calculate_burnout_risk(agg_df)}
        salary = {r['emp_code']: r for r in self.estimate_salary_impact(agg_df)}
        
        # Combine everything into an employee-centric dictionary
        employee_analytics = {}
        for _, row in agg_df.iterrows():
            code = row['emp_code']
            employee_analytics[code] = {
                'emp_code': code,
                'name': row['name'],
                'absenteeism_prediction': absenteeism.get(code),
                'overtime_forecast': overtime.get(code),
                'promotion_score': promotion.get(code),
                'reliability': reliability.get(code),
                'burnout_risk': burnout.get(code),
                'salary_impact': salary.get(code)
            }
            
        # Department / High-level Aggregates for HR Dashboard
        hr_dashboard = {
            'total_employees_analyzed': len(agg_df),
            'high_burnout_count': sum(1 for v in burnout.values() if v['burnout_risk'] == 'High'),
            'high_flight_risk_count': sum(1 for v in absenteeism.values() if v['risk_level'] == 'High'),
            'top_promotion_candidates': sorted(promotion.values(), key=lambda x: x['promotion_score'], reverse=True)[:3],
            'department_avg_reliability': round(sum(v['reliability_score'] for v in reliability.values()) / len(reliability) if reliability else 0, 1),
            'total_overtime_forecast_next_week': round(sum(v['next_week_overtime_est'] for v in overtime.values()), 1)
        }
        
        return {
            "status": "success",
            "employees": employee_analytics,
            "hr_dashboard": hr_dashboard
        }

