import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Clients from './pages/platform/Clients';
import Institutions from './pages/platform/Institutions';
import Users from './pages/platform/Users';
import FeeTypes from './pages/fees/FeeTypes';
import FeeAssignments from './pages/fees/FeeAssignments';
import FeePayments from './pages/fees/FeePayments';
import Homeworks from './pages/homework/Homeworks';
import Submissions from './pages/homework/Submissions';
import Grades from './pages/homework/Grades';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        {/* Platform management */}
        <Route path="/platform/clients" element={<Clients />} />
        <Route path="/platform/institutions" element={<Institutions />} />
        <Route path="/platform/users" element={<Users />} />

        {/* Fees module */}
        <Route path="/fees" element={<FeeTypes />} />
        <Route path="/fees/assignments" element={<FeeAssignments />} />
        <Route path="/fees/payments" element={<FeePayments />} />

        {/* Homework module */}
        <Route path="/homework" element={<Homeworks />} />
        <Route path="/homework/:id/submissions" element={<Submissions />} />
        <Route path="/homework/grades" element={<Grades />} />
      </Route>
      <Route path="*" element={<Navigate to="/platform/clients" />} />
    </Routes>
  );
}
