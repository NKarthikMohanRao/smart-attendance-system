import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

interface EmployeeAnalyticsData {
  emp_code: string;
  name: string;
  absenteeism_prediction: { probability: number; risk_level: string; reason: string; action: string };
  overtime_forecast: { next_week_overtime_est: number; trend: string; reason: string };
  promotion_score: { promotion_score: number; strengths: string[]; weaknesses: string[]; suggestion: string };
  reliability: { reliability_score: number; grade: string };
  burnout_risk: { burnout_risk: string; reason: string; recommendation: string };
  salary_impact: { base_earnings: number; overtime_earnings: number; late_penalty: number; estimated_total: number };
}

const EmployeeAnalytics: React.FC = () => {
  const [data, setData] = useState<EmployeeAnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const empCode = searchParams.get('emp_code') || '';

  const fetchAnalytics = async (code: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/analytics/employee/${code}`);
      if (!res.ok) throw new Error('Employee not found or no data available.');
      const json = await res.json();
      setData(json);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (empCode) {
      fetchAnalytics(empCode);
    }
  }, [empCode]);

  const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    setSearchParams({ emp_code: formData.get('emp_code') as string });
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1>My AI Analytics</h1>
          <p>Personalized insights, predictions, and payroll estimates</p>
        </div>
        
        <form onSubmit={handleSearch} className="filter-group">
          <input type="text" name="emp_code" placeholder="Enter Emp Code (e.g., EMP101)" defaultValue={empCode} required />
          <button type="submit" className="btn">Analyze</button>
        </form>
      </div>

      {loading && <div style={{ padding: '2rem' }}>Running AI models...</div>}
      {error && <div className="status-message error">{error}</div>}

      {data && !loading && (
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          
          <div className="employee-profile" style={{ marginBottom: 0 }}>
            <div className="employee-info">
              <h2>{data.name}</h2>
              <div className="employee-meta">
                <span className="badge badge-normal">{data.emp_code}</span>
                <span className="badge" style={{ background: 'var(--primary)', color: '#fff' }}>Reliability: {data.reliability.grade} ({data.reliability.reliability_score})</span>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
            
            {/* Absenteeism & Flight Risk */}
            <div className="card" style={{ borderTop: `4px solid ${data.absenteeism_prediction.risk_level === 'High' ? 'var(--danger)' : data.absenteeism_prediction.risk_level === 'Medium' ? 'var(--warning)' : 'var(--success)'}` }}>
              <h3>🔮 Absenteeism Forecast</h3>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', margin: '1rem 0' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1 }}>{data.absenteeism_prediction.probability}%</span>
                <span style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Probability</span>
              </div>
              <p><strong>Risk Level:</strong> {data.absenteeism_prediction.risk_level}</p>
              <div style={{ padding: '0.75rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                <strong>XAI Reason:</strong> {data.absenteeism_prediction.reason}<br/><br/>
                <strong>AI Action:</strong> {data.absenteeism_prediction.action}
              </div>
            </div>

            {/* Burnout Risk */}
            <div className="card" style={{ borderTop: `4px solid ${data.burnout_risk.burnout_risk === 'High' ? 'var(--danger)' : data.burnout_risk.burnout_risk === 'Medium' ? 'var(--warning)' : 'var(--success)'}` }}>
              <h3>🔥 Burnout Risk</h3>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', margin: '1rem 0' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1 }}>{data.burnout_risk.burnout_risk}</span>
                <span style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Risk</span>
              </div>
              <div style={{ padding: '0.75rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                <strong>XAI Reason:</strong> {data.burnout_risk.reason}<br/><br/>
                <strong>AI Action:</strong> {data.burnout_risk.recommendation}
              </div>
            </div>

            {/* Overtime Forecast */}
            <div className="card" style={{ borderTop: '4px solid var(--info)' }}>
              <h3>⚡ Overtime Forecast (Next Wk)</h3>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', margin: '1rem 0' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1 }}>{data.overtime_forecast.next_week_overtime_est}h</span>
              </div>
              <p><strong>Trend:</strong> {data.overtime_forecast.trend}</p>
              <div style={{ padding: '0.75rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                <strong>XAI Reason:</strong> {data.overtime_forecast.reason}
              </div>
            </div>

            {/* Promotion Readiness */}
            <div className="card" style={{ borderTop: '4px solid var(--primary)' }}>
              <h3>⭐ Promotion Readiness</h3>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', margin: '1rem 0' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1 }}>{data.promotion_score.promotion_score}</span>
                <span style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}>/ 100</span>
              </div>
              <div style={{ padding: '0.75rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                <strong>Strengths:</strong> {data.promotion_score.strengths.join(', ') || 'None identified'}<br/><br/>
                <strong>Weaknesses:</strong> {data.promotion_score.weaknesses.join(', ') || 'None identified'}<br/><br/>
                <strong>AI Action:</strong> {data.promotion_score.suggestion}
              </div>
            </div>

            {/* Salary Impact Analytics */}
            <div className="card" style={{ gridColumn: '1 / -1', borderTop: '4px solid #10B981' }}>
              <h3>💰 Estimated Salary Impact Analytics</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>Based on $25/hr standard rate simulation</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ flex: 1, padding: '1rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Base Earnings</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>${data.salary_impact.base_earnings}</div>
                </div>
                <div style={{ flex: 1, padding: '1rem', background: 'rgba(16, 185, 129, 0.1)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.9rem', color: '#10B981' }}>+ Overtime</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#10B981' }}>${data.salary_impact.overtime_earnings}</div>
                </div>
                <div style={{ flex: 1, padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.9rem', color: '#EF4444' }}>- Late Penalty</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#EF4444' }}>${data.salary_impact.late_penalty}</div>
                </div>
                <div style={{ flex: 1, padding: '1rem', background: 'var(--primary)', color: '#fff', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.8)' }}>Net Estimate</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>${data.salary_impact.estimated_total}</div>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </>
  );
};

export default EmployeeAnalytics;
