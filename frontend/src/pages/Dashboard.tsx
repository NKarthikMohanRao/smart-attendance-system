import React, { useEffect, useState } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend);

interface DashboardData {
  is_empty_db: boolean;
  start_date: string;
  end_date: string;
  total_employees?: number;
  total_overtime_hours?: number;
  count_undershift_days?: number;
  count_missed_punch_days?: number;
  count_absent_days?: number;
  count_normal_days?: number;
  count_overtime_days?: number;
  standard_shift?: number;
  min_shift?: number;
}

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const fetchData = async (start?: string, end?: string) => {
    try {
      let url = '/api/summary';
      if (start && end) {
        url += `?start_date=${start}&end_date=${end}`;
      }
      const res = await fetch(url);
      const json = await res.json();
      setData(json);
      setStartDate(json.start_date);
      setEndDate(json.end_date);
    } catch (err) {
      console.error('Failed to fetch dashboard data', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleFilter = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData(startDate, endDate);
  };

  if (!data) return <div style={{ padding: '2rem' }}>Loading...</div>;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Attendance &amp; Shift Dashboard</h1>
          <p>Real-time analytics and shift compliance tracking across your workforce</p>
        </div>
        
        {!data.is_empty_db && (
          <form onSubmit={handleFilter} className="filter-group">
            <span className="filter-label">Date Range:</span>
            <input 
              type="date" 
              value={startDate} 
              onChange={e => setStartDate(e.target.value)} 
              required 
            />
            <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
            <input 
              type="date" 
              value={endDate} 
              onChange={e => setEndDate(e.target.value)} 
              required 
            />
            <button type="submit" className="btn">Filter</button>
            <button type="button" className="btn btn-secondary" onClick={() => fetchData()}>Reset</button>
          </form>
        )}
      </div>

      {data.is_empty_db ? (
        <div className="empty-state">
          <div className="empty-icon">🚀</div>
          <h3>No Attendance Data Yet</h3>
          <p>Your database (<code>attendance.db</code>) currently has no registered employees or attendance logs. Get started by running the system scripts below to generate data.</p>
          <div className="empty-steps">
            <div className="step-card">
              <span className="step-num">1</span>
              <div>
                <h4>Register Employees</h4>
                <code>python register_faces.py</code>
              </div>
            </div>
            <div className="step-card">
              <span className="step-num">2</span>
              <div>
                <h4>Run Live Camera</h4>
                <code>python attendance_system.py</code>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-header">
                <span className="stat-title">Total Employees</span>
                <div className="stat-icon" style={{ color: '#A855F7' }}>👥</div>
              </div>
              <div className="stat-value">{data.total_employees}</div>
              <div className="stat-sub">Registered workforce</div>
            </div>

            <div className="stat-card">
              <div className="stat-header">
                <span className="stat-title">Total Overtime</span>
                <div className="stat-icon" style={{ color: '#38BDF8' }}>⚡</div>
              </div>
              <div className="stat-value">{data.total_overtime_hours?.toFixed(1)} <span style={{ fontSize: '1.25rem' }}>hrs</span></div>
              <div className="stat-sub">Beyond {data.standard_shift}h shift</div>
            </div>

            <div className="stat-card">
              <div className="stat-header">
                <span className="stat-title">Under-Shift Days</span>
                <div className="stat-icon" style={{ color: '#F59E0B' }}>⚠️</div>
              </div>
              <div className="stat-value">{data.count_undershift_days}</div>
              <div className="stat-sub">Worked below {data.min_shift}h minimum</div>
            </div>

            <div className="stat-card">
              <div className="stat-header">
                <span className="stat-title">Missed-Punch Days</span>
                <div className="stat-icon" style={{ color: '#EF4444' }}>❌</div>
              </div>
              <div className="stat-value">{data.count_missed_punch_days}</div>
              <div className="stat-sub">Odd number of IN/OUT events</div>
            </div>

            <div className="stat-card">
              <div className="stat-header">
                <span className="stat-title">Absent Days</span>
                <div className="stat-icon" style={{ color: '#94A3B8' }}>🏠</div>
              </div>
              <div className="stat-value">{data.count_absent_days}</div>
              <div className="stat-sub">Zero punches recorded</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">Attendance Compliance Distribution</span>
                <span className="badge badge-normal">{data.start_date} &rarr; {data.end_date}</span>
              </div>
              <div style={{ height: '260px', position: 'relative' }}>
                <Doughnut 
                  data={{
                    labels: ['Normal / Complete', 'Overtime Days', 'Under-Shift Days', 'Missed-Punch Days', 'Absent Days'],
                    datasets: [{
                      data: [
                        data.count_normal_days || 0,
                        data.count_overtime_days || 0,
                        data.count_undershift_days || 0,
                        data.count_missed_punch_days || 0,
                        data.count_absent_days || 0
                      ],
                      backgroundColor: ['#10B981', '#38BDF8', '#F59E0B', '#EF4444', '#64748B'],
                      borderWidth: 0,
                      hoverOffset: 6
                    }]
                  }}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { position: 'right', labels: { color: '#94A3B8', font: { family: 'Inter', size: 12 }, padding: 16 } }
                    }
                  }}
                />
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Quick Policy Overview</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.8rem 1rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <span>Standard Working Shift</span>
                  <strong style={{ color: 'var(--primary)' }}>{data.standard_shift} Hours</strong>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.8rem 1rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <span>Minimum Shift Alert Threshold</span>
                  <strong style={{ color: 'var(--warning)' }}>{data.min_shift} Hours</strong>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.8rem 1rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <span>Missed Punch Condition</span>
                  <span className="badge badge-missed">Odd # Events</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.8rem 1rem', background: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <span>Zero Punches Condition</span>
                  <span className="badge badge-absent">Absent</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default Dashboard;
