import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface DashboardAnalytics {
  total_employees_analyzed: number;
  high_burnout_count: number;
  high_flight_risk_count: number;
  total_overtime_forecast_next_week: number;
  department_avg_reliability: number;
  top_promotion_candidates: Array<{
    emp_code: string;
    promotion_score: number;
    strengths: string[];
    suggestion: string;
  }>;
}

const HRAnalytics: React.FC = () => {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await fetch('/api/analytics/dashboard');
        if (!res.ok) throw new Error('Failed to fetch analytics');
        const json = await res.json();
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };
    
    fetchAnalytics();
  }, []);

  if (loading) return <div style={{ padding: '2rem' }}>Loading AI Models...</div>;
  if (error) return <div className="status-message error">{error}</div>;
  if (!data) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>🤖 Predictive HR Analytics</h1>
          <p>AI-powered workforce intelligence and decision support</p>
        </div>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="stat-card" style={{ borderLeft: '4px solid #10B981' }}>
          <div className="stat-header">
            <span className="stat-title">Analyzed Workforce</span>
          </div>
          <div className="stat-value">{data.total_employees_analyzed}</div>
          <div className="stat-sub">Employees scored</div>
        </div>
        
        <div className="stat-card" style={{ borderLeft: '4px solid #EF4444' }}>
          <div className="stat-header">
            <span className="stat-title">High Flight Risk</span>
          </div>
          <div className="stat-value">{data.high_flight_risk_count}</div>
          <div className="stat-sub">Likely Absent Next Week</div>
        </div>
        
        <div className="stat-card" style={{ borderLeft: '4px solid #F59E0B' }}>
          <div className="stat-header">
            <span className="stat-title">High Burnout Risk</span>
          </div>
          <div className="stat-value">{data.high_burnout_count}</div>
          <div className="stat-sub">Needs manager review</div>
        </div>

        <div className="stat-card" style={{ borderLeft: '4px solid #38BDF8' }}>
          <div className="stat-header">
            <span className="stat-title">OT Forecast (Next Wk)</span>
          </div>
          <div className="stat-value">{data.total_overtime_forecast_next_week}h</div>
          <div className="stat-sub">Estimated Department Overtime</div>
        </div>

        <div className="stat-card" style={{ borderLeft: '4px solid #A855F7' }}>
          <div className="stat-header">
            <span className="stat-title">Avg Reliability Score</span>
          </div>
          <div className="stat-value">{data.department_avg_reliability} / 100</div>
          <div className="stat-sub">Workforce consistency index</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: '2rem' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>🏆 Top Promotion Candidates</h2>
        {data.top_promotion_candidates.length > 0 ? (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {data.top_promotion_candidates.map((emp) => (
              <div key={emp.emp_code} style={{ padding: '1rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{emp.emp_code}</h3>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                    {emp.strengths.map(s => <span key={s} className="badge badge-normal">{s}</span>)}
                  </div>
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.9rem', color: 'var(--text-muted)' }}>AI Suggestion: {emp.suggestion}</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: emp.promotion_score >= 80 ? 'var(--success)' : 'var(--primary)' }}>
                    {emp.promotion_score} / 100
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Readiness Score</div>
                  <Link to={`/employee-analytics?emp_code=${emp.emp_code}`} style={{ fontSize: '0.9rem', color: 'var(--primary)', marginTop: '0.5rem', display: 'inline-block' }}>View Details &rarr;</Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)' }}>Not enough data to recommend promotions.</p>
        )}
      </div>

    </>
  );
};

export default HRAnalytics;
