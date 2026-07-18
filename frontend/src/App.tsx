import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
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
        <Route path="/fees" element={<FeeTypes />} />
        <Route path="/fees/assignments" element={<FeeAssignments />} />
        <Route path="/fees/payments" element={<FeePayments />} />
        <Route path="/homework" element={<Homeworks />} />
        <Route path="/homework/:id/submissions" element={<Submissions />} />
        <Route path="/homework/grades" element={<Grades />} />
      </Route>
      <Route path="*" element={<Navigate to="/fees" />} />
    </Routes>
  );
}
