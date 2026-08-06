
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import EmployeeDetail from './pages/EmployeeDetail';
import Report from './pages/Report';
import Register from './pages/Register';
import Kiosk from './pages/Kiosk';
import HRAnalytics from './pages/HRAnalytics';
import EmployeeAnalytics from './pages/EmployeeAnalytics';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="employee" element={<EmployeeDetail />} />
          <Route path="report" element={<Report />} />
          <Route path="register" element={<Register />} />
          <Route path="kiosk" element={<Kiosk />} />
          <Route path="hr-analytics" element={<HRAnalytics />} />
          <Route path="employee-analytics" element={<EmployeeAnalytics />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
