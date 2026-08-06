import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

interface DailyRecord {
  date: string;
  emp_code: string;
  name: string;
  department: string;
  login_time: string | null;
  logout_time: string | null;
  hours_worked: number;
  overtime: number;
  flags: string[];
}

interface ReportData {
  is_empty_db: boolean;
  start_date: string;
  end_date: string;
  all_records: DailyRecord[];
  min_shift: number;
}

const Report: React.FC = () => {
  const [data, setData] = useState<ReportData | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [filterFlag, setFilterFlag] = useState('all');
  const [searchText, setSearchText] = useState('');

  const startDate = searchParams.get('start_date') || '';
  const endDate = searchParams.get('end_date') || '';

  const fetchData = async () => {
    try {
      let url = 'http://127.0.0.1:5000/api/report?';
      if (startDate) url += `start_date=${startDate}&`;
      if (endDate) url += `end_date=${endDate}`;
      
      const res = await fetch(url);
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('Failed to fetch report data', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, [startDate, endDate]);

  const handleFilter = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    setSearchParams({
      start_date: formData.get('start_date') as string,
      end_date: formData.get('end_date') as string,
    });
  };

  if (!data) return <div style={{ padding: '2rem' }}>Loading...</div>;

  const filteredRecords = data.all_records?.filter(r => {
    const flagMatch = filterFlag === 'all' || r.flags.some(f => f.toLowerCase() === filterFlag.toLowerCase());
    const textMatch = !searchText || Object.values(r).join(' ').toLowerCase().includes(searchText.toLowerCase());
    return flagMatch && textMatch;
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1>All-Employees Report</h1>
          <p>Comprehensive tabular view of all attendance records</p>
        </div>
        
        {!data.is_empty_db && (
          <form onSubmit={handleFilter} className="filter-group">
            <span className="filter-label">Date Range:</span>
            <input type="date" name="start_date" defaultValue={data.start_date} required />
            <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
            <input type="date" name="end_date" defaultValue={data.end_date} required />
            <button type="submit" className="btn">Apply</button>
          </form>
        )}
      </div>

      {data.is_empty_db ? (
        <div className="empty-state">
          <div className="empty-icon">📂</div>
          <h3>No Data Available</h3>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          
          <div className="table-toolbar">
            <div className="table-search">
              <span style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', opacity: 0.5 }}>🔍</span>
              <input 
                type="text" 
                placeholder="Search by name, code, or department..." 
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
              />
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="filter-label" style={{ fontSize: '0.875rem' }}>Filter Status:</span>
              <select value={filterFlag} onChange={e => setFilterFlag(e.target.value)} style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', outline: 'none' }}>
                <option value="all">All Statuses</option>
                <option value="normal">Normal</option>
                <option value="absent">Absent</option>
                <option value="missed punch">Missed Punch</option>
                <option value="under-shift">Under-Shift</option>
                <option value="overtime">Overtime</option>
              </select>
            </div>
          </div>

          <div className="table-responsive" style={{ maxHeight: '600px', overflowY: 'auto' }}>
            <table className="table" data-sortable="true" id="reportTable">
              <thead style={{ position: 'sticky', top: 0, zIndex: 1, backgroundColor: 'var(--bg-body)' }}>
                <tr>
                  <th>Date</th>
                  <th>Emp Code</th>
                  <th>Name</th>
                  <th>Dept</th>
                  <th>Login</th>
                  <th>Logout</th>
                  <th>Hours</th>
                  <th>Overtime</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords?.map((r, i) => (
                  <tr key={i} className={r.flags.includes('Absent') ? 'empty-row' : ''}>
                    <td style={{ whiteSpace: 'nowrap' }}>{r.date}</td>
                    <td><strong>{r.emp_code}</strong></td>
                    <td style={{ fontWeight: 600 }}>{r.name}</td>
                    <td><span className="badge" style={{ background: 'var(--bg-body)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}>{r.department}</span></td>
                    <td>{r.login_time ? <span className="time-badge in">{r.login_time}</span> : '-'}</td>
                    <td>{r.logout_time ? <span className="time-badge out">{r.logout_time}</span> : '-'}</td>
                    <td>
                      <span style={{ fontWeight: r.hours_worked < data.min_shift && r.hours_worked > 0 ? 600 : 'normal', color: r.hours_worked < data.min_shift && r.hours_worked > 0 ? 'var(--warning)' : 'inherit' }}>
                        {r.hours_worked.toFixed(2)}h
                      </span>
                    </td>
                    <td>
                      {r.overtime > 0 ? <span style={{ color: 'var(--info)', fontWeight: 600 }}>+{r.overtime.toFixed(2)}h</span> : '-'}
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
                {filteredRecords?.length === 0 && (
                  <tr>
                    <td colSpan={9} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                      No matching records found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
};

export default Report;
