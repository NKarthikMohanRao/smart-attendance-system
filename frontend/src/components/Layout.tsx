import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

const Layout: React.FC = () => {
  const location = useLocation();
  const activePage = location.pathname;

  return (
    <>
      <nav className="navbar">
        <Link to="/" className="brand">
          <div className="brand-icon">⚡</div>
          <span>Smart Attendance</span>
        </Link>
        <div className="nav-links">
          <Link to="/" className={`nav-link ${activePage === '/' ? 'active' : ''}`}>Dashboard</Link>
          <Link to="/hr-analytics" className={`nav-link ${activePage === '/hr-analytics' ? 'active' : ''}`} style={{color: 'var(--primary)'}}>🤖 AI Analytics</Link>
          <Link to="/employee" className={`nav-link ${activePage === '/employee' ? 'active' : ''}`}>Employee Detail</Link>
          <Link to="/employee-analytics" className={`nav-link ${activePage === '/employee-analytics' ? 'active' : ''}`}>My Analytics</Link>
          <Link to="/report" className={`nav-link ${activePage === '/report' ? 'active' : ''}`}>All-Employees Report</Link>
          <Link to="/register" className={`nav-link ${activePage === '/register' ? 'active' : ''}`}>Register User</Link>
          <Link to="/kiosk" className={`nav-link ${activePage === '/kiosk' ? 'active' : ''}`} style={{ color: 'var(--primary)', fontWeight: 600 }}>🔴 Live Kiosk</Link>
        </div>
      </nav>

      <main className="container">
        <Outlet />
      </main>

      <footer className="footer">
        <p>⚡ Smart Attendance System &bull; Classic Enterprise Reporting</p>
      </footer>
    </>
  );
};

export default Layout;
