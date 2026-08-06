import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

interface Employee {
  emp_code: string;
  name: string;
  department: string;
  designation: string;
}

interface DailyRecord {
  date: string;
  login_time: string | null;
  logout_time: string | null;
  hours_worked: number;
  overtime: number;
  flags: string[];
}

interface EmployeeDetailData {
  is_empty_db: boolean;
  employees: Employee[];
  selected_emp: Employee | null;
  daily_records: DailyRecord[];
  start_date: string;
  end_date: string;
  total_emp_hours: number;
  total_emp_overtime: number;
  count_emp_undershift: number;
  count_emp_missed: number;
  min_shift: number;
}

const EmployeeDetail: React.FC = () => {
  const [data, setData] = useState<EmployeeDetailData | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  
  const empCode = searchParams.get('emp_code') || '';
  const startDate = searchParams.get('start_date') || '';
  const endDate = searchParams.get('end_date') || '';

  const fetchData = async () => {
    try {
      let url = '/api/employee?';
      if (empCode) url += `emp_code=${empCode}&`;
      if (startDate) url += `start_date=${startDate}&`;
      if (endDate) url += `end_date=${endDate}`;
      
      const res = await fetch(url);
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('Failed to fetch employee detail', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, [empCode, startDate, endDate]);

  const handleFilter = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    setSearchParams({
      emp_code: formData.get('emp_code') as string,
      start_date: formData.get('start_date') as string,
      end_date: formData.get('end_date') as string,
    });
  };

  const handleDelete = async () => {
    if (!data?.selected_emp) return;
    if (!window.confirm(`Are you sure you want to delete ${data.selected_emp.name}? This will remove all their data and face encodings.`)) return;
    
    try {
      const res = await fetch(`/api/employee/${data.selected_emp.emp_code}`, { method: 'DELETE' });
      if (res.ok) {
        alert('Employee deleted successfully');
        window.location.href = '/employee';
      } else {
        const json = await res.json();
        alert('Failed to delete employee: ' + json.error);
      }
    } catch(err) {
      alert('Error: ' + err);
    }
  };

  if (!data) return <div style={{ padding: '2rem' }}>Loading...</div>;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Employee Detail</h1>
          <p>Individual attendance breakdown and shift history</p>
        </div>
        
        {!data.is_empty_db && (
          <form onSubmit={handleFilter} className="filter-group">
            <span className="filter-label">Select Employee:</span>
            <select name="emp_code" defaultValue={data.selected_emp?.emp_code || ''} required>
              {data.employees?.map(emp => (
                <option key={emp.emp_code} value={emp.emp_code}>
                  {emp.name} ({emp.emp_code})
                </option>
              ))}
            </select>
            <span style={{ marginLeft: '1rem' }} className="filter-label">Date Range:</span>
            <input type="date" name="start_date" defaultValue={data.start_date} required />
            <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
            <input type="date" name="end_date" defaultValue={data.end_date} required />
            <button type="submit" className="btn">View</button>
          </form>
        )}
      </div>

      {data.is_empty_db ? (
        <div className="empty-state">
          <div className="empty-icon">📂</div>
          <h3>No Data Available</h3>
          <p>Please register employees and log attendance first.</p>
        </div>
      ) : data.selected_emp ? (
        <>
          <div className="employee-profile">
            <div className="employee-info">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
                <h2 style={{ margin: 0 }}>{data.selected_emp.name}</h2>
                <button onClick={handleDelete} className="btn" style={{ background: 'var(--danger)', color: 'white', padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}>Delete Employee</button>
              </div>
              <div className="employee-meta" style={{ marginTop: '0.5rem' }}>
                <span className="badge badge-normal">Code: {data.selected_emp.emp_code}</span>
                <span className="badge" style={{ background: 'var(--bg-body)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}>{data.selected_emp.department}</span>
                <span className="badge" style={{ background: 'var(--bg-body)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}>{data.selected_emp.designation}</span>
              </div>
            </div>
            <div className="employee-stats">
              <div className="emp-stat">
                <div className="emp-stat-val">{data.total_emp_hours?.toFixed(1)}</div>
                <div className="emp-stat-lbl">Total Hours</div>
              </div>
              <div className="emp-stat">
                <div className="emp-stat-val">{data.total_emp_overtime?.toFixed(1)}</div>
                <div className="emp-stat-lbl">Overtime</div>
              </div>
              <div className="emp-stat">
                <div className="emp-stat-val">{data.count_emp_undershift}</div>
                <div className="emp-stat-lbl">Under-Shifts</div>
              </div>
              <div className="emp-stat">
                <div className="emp-stat-val">{data.count_emp_missed}</div>
                <div className="emp-stat-lbl">Missed Punches</div>
              </div>
            </div>
          </div>

          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div className="table-responsive">
              <table className="table" data-sortable="true">
                <thead>
                  <tr>
                    <th data-sort="date" data-sort-type="date">Date <span className="sort-indicator"></span></th>
                    <th>Login</th>
                    <th>Logout</th>
                    <th data-sort="hours" data-sort-type="number">Hours <span className="sort-indicator"></span></th>
                    <th data-sort="overtime" data-sort-type="number">Overtime <span className="sort-indicator"></span></th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.daily_records?.map((r, i) => (
                    <tr key={i} className={r.flags.includes('Absent') ? 'empty-row' : ''}>
                      <td data-value={r.date}><strong>{r.date}</strong></td>
                      <td>
                        {r.login_time ? <span className="time-badge in">IN: {r.login_time}</span> : <span style={{ color: 'var(--text-muted)' }}>-</span>}
                      </td>
                      <td>
                        {r.logout_time ? <span className="time-badge out">OUT: {r.logout_time}</span> : <span style={{ color: 'var(--text-muted)' }}>-</span>}
                      </td>
                      <td data-value={r.hours_worked}>
                        <span style={{ fontWeight: r.hours_worked < data.min_shift && r.hours_worked > 0 ? 600 : 'normal', color: r.hours_worked < data.min_shift && r.hours_worked > 0 ? 'var(--warning)' : 'inherit' }}>
                          {r.hours_worked.toFixed(2)}h
                        </span>
                      </td>
                      <td data-value={r.overtime}>
                        {r.overtime > 0 ? <span style={{ color: 'var(--info)', fontWeight: 600 }}>+{r.overtime.toFixed(2)}h</span> : <span style={{ color: 'var(--text-muted)' }}>0.00h</span>}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                          {r.flags.map(f => {
                            let bClass = 'badge-normal';
                            if (f === 'Absent') bClass = 'badge-absent';
                            else if (f === 'Missed Punch') bClass = 'badge-missed';
                            else if (f === 'Under-Shift') bClass = 'badge-undershift';
                            else if (f === 'Overtime') bClass = 'badge-overtime';
                            return <span key={f} className={`badge ${bClass}`}>{f}</span>;
                          })}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {(!data.daily_records || data.daily_records.length === 0) && (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                        No records found for the selected period.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </>
  );
};

export default EmployeeDetail;
