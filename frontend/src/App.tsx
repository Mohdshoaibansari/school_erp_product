import { Route, Routes } from 'react-router-dom';
import { PublicOnly } from './core/auth/PublicOnly';
import { RequireAuth } from './core/auth/RequireAuth';
import { RequireRole } from './core/access/RequireRole';
import { AppShell } from './shell/AppShell';
import { NotFound } from './shell/NotFound';
import { HomeRedirect } from './shell/HomeRedirect';

import { Login } from './features/auth/Login';
import { Activate } from './features/auth/Activate';
import { OtpVerify } from './features/auth/OtpVerify';
import { ResetPassword } from './features/auth/ResetPassword';
import { ChangePassword } from './features/auth/ChangePassword';

import { Clients } from './features/platform/Clients';
import { ClientUsers } from './features/platform/ClientUsers';
import { InstitutionTypes } from './features/platform/InstitutionTypes';
import { OwnershipTransfers } from './features/platform/OwnershipTransfers';

import { Institutions } from './features/institutions/Institutions';
import { OrgUnits } from './features/institutions/OrgUnits';

import { Users } from './features/users/Users';
import { UserDetail } from './features/users/UserDetail';

import { AcademicYears } from './features/academic/AcademicYears';
import { StructureView } from './features/academic/StructureView';
import { Subjects } from './features/academic/Subjects';
import { SubjectGroups } from './features/academic/SubjectGroups';

import { ConfigKeys } from './features/config/ConfigKeys';
import { ConfigAudit } from './features/config/ConfigAudit';

import { FeeTypes } from './features/fees/FeeTypes';
import { FeeAssignments } from './features/fees/FeeAssignments';
import { Payments } from './features/fees/Payments';

import { Homeworks } from './features/homework/Homeworks';
import { Submissions } from './features/homework/Submissions';
import { Grades } from './features/homework/Grades';

/** Placeholder for views that need additional context selection. */
function ComingSoon({ title }: { title: string }) {
  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h2>{title}</h2>
      <p style={{ color: '#64748B' }}>This view is coming soon.</p>
    </div>
  );
}

/**
 * Route table (library-mode React Router v7) — single source of truth for the
 * reachable surface (design.md §3.1, REQ-SHELL-06). Role gating is applied per
 * group via <RequireRole>.
 */
export default function App() {
  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/login" element={<Login />} />
        <Route path="/activate" element={<Activate />} />
        <Route path="/otp/verify" element={<OtpVerify />} />
        <Route path="/password/reset" element={<ResetPassword />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route element={<RequireRole />}>
            <Route path="/platform/clients" element={<Clients />} />
            <Route path="/platform/clients/:clientId" element={<ClientUsers />} />
          </Route>
          <Route element={<RequireRole />}>
            <Route path="/platform/institution-types" element={<InstitutionTypes />} />
          </Route>
          <Route element={<RequireRole />}>
            <Route
              path="/platform/ownership-transfers"
              element={<OwnershipTransfers />}
            />
          </Route>

          <Route element={<RequireRole />}>
            <Route path="/institutions" element={<Institutions />} />
            <Route
              path="/institutions/:institutionId/org-units"
              element={<OrgUnits />}
            />
          </Route>

          <Route element={<RequireRole />}>
            <Route path="/users" element={<Users />} />
            <Route path="/users/:userId" element={<UserDetail />} />
          </Route>

          <Route element={<RequireRole />}>
            <Route path="/academic/years" element={<AcademicYears />} />
            <Route
              path="/academic/years/:yearId/structure"
              element={<StructureView />}
            />
            <Route path="/academic/subjects" element={<Subjects />} />
            <Route
              path="/academic/subject-groups"
              element={<SubjectGroups />}
            />
            <Route
              path="/academic/assignments"
              element={<ComingSoon title="Teacher Assignments" />}
            />
            <Route
              path="/academic/enrollments"
              element={<ComingSoon title="Enrollments" />}
            />
          </Route>

          <Route element={<RequireRole />}>
            <Route path="/config/keys" element={<ConfigKeys />} />
            <Route path="/config/audit" element={<ConfigAudit />} />
          </Route>

          <Route element={<RequireRole />}>
            <Route path="/fees/types" element={<FeeTypes />} />
            <Route path="/fees/assignments" element={<FeeAssignments />} />
            <Route path="/fees/payments" element={<Payments />} />
          </Route>

          <Route element={<RequireRole />}>
            <Route path="/homework" element={<Homeworks />} />
            <Route path="/homework/submissions" element={<Submissions />} />
            <Route
              path="/homework/:hwId/submissions"
              element={<Submissions />}
            />
            <Route path="/homework/grades" element={<Grades />} />
          </Route>

          {/* Student views */}
          <Route element={<RequireRole />}>
            <Route path="/student/homework" element={<ComingSoon title="My Homework" />} />
            <Route path="/student/grades" element={<ComingSoon title="My Grades" />} />
            <Route path="/student/fees" element={<ComingSoon title="My Fees" />} />
          </Route>

          {/* Parent views */}
          <Route element={<RequireRole />}>
            <Route path="/parent/profile" element={<ComingSoon title="My Profile" />} />
          </Route>

          <Route path="/account/change-password" element={<ChangePassword />} />
        </Route>
      </Route>

      <Route path="/" element={<HomeRedirect />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
