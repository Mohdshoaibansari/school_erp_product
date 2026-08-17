import type { Role } from './roles';

export interface NavItem {
  label: string;
  path: string;
  roles: Role[];
  icon?: string;
}

/**
 * Declarative nav → role map (REQ-SHELL-03, REQ-SHELL-10).
 *
 * Role lists are derived from actual backend Casbin role_permission rows:
 *   - platform_owner: Casbin bypass (D28) → full access to all modules
 *   - client_director: tenant-scoped perms from migrations 009, 016, 019, 020
 *   - institution_admin / Admin: institution-scoped perms from migrations 002-020
 *   - Principal, HOD, Teacher, Staff, Student, Parent: read-only or limited perms
 *
 * Reference: docs/frontend-gap-analysis.md §13
 */
export const NAV_ITEMS: NavItem[] = [
  // ── Platform Management ─────────────────────────────
  { label: 'Clients', path: '/platform/clients', roles: ['platform_owner'] },
  {
    label: 'Institution Types',
    path: '/platform/institution-types',
    roles: ['platform_owner'],
  },
  {
    label: 'Ownership Transfers',
    path: '/platform/ownership-transfers',
    roles: ['platform_owner'],
  },

  // ── Institutions & Org Units ────────────────────────
  // client_director: institution.* + org_unit.* (tenant scope)
  // platform_owner: Casbin bypass → full access
  {
    label: 'Institutions',
    path: '/institutions',
    roles: ['platform_owner', 'client_director'],
  },

  // ── User Management ─────────────────────────────────
  // client_director: user.create/read/update/suspend (tenant)
  // institution_admin/Admin: user.* (institution)
  // Principal/HOD/Staff: user.read only
  // Teacher: user.read/update (own only)
  // Student/Parent: user.read (own only)
  {
    label: 'Users',
    path: '/users',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
      'hod',
      'staff',
    ],
  },

  // ── Academic Structure ──────────────────────────────
  // client_director: academic_year.* + enrollment.* + teacher_assignment.* (tenant)
  // institution_admin/Admin: all academic perms (institution)
  // Principal/HOD/Teacher/Staff/Student/Parent: academic_year.read, enrollment.read, teacher_assignment.read
  {
    label: 'Academic Years',
    path: '/academic/years',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
    ],
  },
  {
    label: 'Structure',
    path: '/academic/structure',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
    ],
  },
  {
    label: 'Subjects',
    path: '/academic/subjects',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
      'hod',
      'teacher',
    ],
  },
  {
    label: 'Subject Groups',
    path: '/academic/subject-groups',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
    ],
  },
  {
    label: 'Teacher Assignments',
    path: '/academic/assignments',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
    ],
  },
  {
    label: 'Enrollments',
    path: '/academic/enrollments',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
    ],
  },

  // ── Configuration ───────────────────────────────────
  // platform_owner: config.* (all)
  // client_director: config.value.create/update/delete + config.key.list + config.audit.read
  // institution_admin/Admin: same as client_director (institution scope)
  {
    label: 'Configuration',
    path: '/config/keys',
    roles: ['platform_owner', 'client_director', 'institution_admin', 'admin'],
  },
  {
    label: 'Config Audit',
    path: '/config/audit',
    roles: ['platform_owner', 'client_director', 'institution_admin', 'admin'],
  },

  // ── Fees ────────────────────────────────────────────
  // client_director: fee.* + fee_assignment.* + payment.* + receipt.read (tenant)
  // institution_admin/Admin: all fee perms (institution)
  // Principal: fee.read, fee_assignment.read, payment.read, receipt.read
  // HOD: fee_assignment.read, payment.read
  // Teacher/Staff: fee_assignment.read
  // Student: fee_assignment.read, payment.read
  {
    label: 'Fee Types',
    path: '/fees/types',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
    ],
  },
  {
    label: 'Fee Assignments',
    path: '/fees/assignments',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
      'hod',
      'teacher',
      'staff',
      'student',
    ],
  },
  {
    label: 'Payments',
    path: '/fees/payments',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
      'hod',
      'student',
    ],
  },

  // ── Homework & Grading ──────────────────────────────
  // Teacher: homework.* + submission.read + grade.* (all CRUD)
  // institution_admin/Admin: homework.read, submission.read, grade.read
  // client_director: homework.read, submission.read, grade.read (tenant)
  // Principal/HOD: homework.read, submission.read, grade.read
  // Student: homework.read, submission.create/read, grade.read
  {
    label: 'Homework',
    path: '/homework',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
      'hod',
      'teacher',
    ],
  },
  {
    label: 'Submissions',
    path: '/homework/submissions',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
      'hod',
      'teacher',
    ],
  },
  {
    label: 'Grades',
    path: '/homework/grades',
    roles: [
      'platform_owner',
      'client_director',
      'institution_admin',
      'admin',
      'principal',
      'hod',
      'teacher',
    ],
  },

  // ── Student Views ───────────────────────────────────
  // Student: homework.read, submission.create/read, grade.read, fee_assignment.read, payment.read
  {
    label: 'My Homework',
    path: '/student/homework',
    roles: ['student'],
  },
  {
    label: 'My Grades',
    path: '/student/grades',
    roles: ['student'],
  },
  {
    label: 'My Fees',
    path: '/student/fees',
    roles: ['student'],
  },

  // ── Parent Views ────────────────────────────────────
  // Parent: user.read (own only) — placeholder until parent_child_relationship exists
  {
    label: 'My Profile',
    path: '/parent/profile',
    roles: ['parent'],
  },
];

export function navItemsForRoles(roles: readonly string[]): NavItem[] {
  return NAV_ITEMS.filter((item) =>
    item.roles.some((role) => roles.includes(role)),
  );
}

/** Roles required to reach a path (longest-prefix match). Empty if unrestricted. */
export function rolesForPath(path: string): Role[] {
  const match = NAV_ITEMS.find((item) => path.startsWith(item.path));
  return match?.roles ?? [];
}
