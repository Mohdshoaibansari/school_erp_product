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
 * Role lists are derived from actual backend Casbin role_permission rows.
 * platform_owner is excluded from institution-level nav items — the sidebar
 * shows only platform-management items for platform owners, even though
 * the Casbin bypass (D28) gives them backend access to everything.
 *
 * Reference: docs/frontend-gap-analysis.md §13
 */
export const NAV_ITEMS: NavItem[] = [
  // ── Platform Management (platform_owner only) ──────
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
  {
    label: 'Institutions',
    path: '/institutions',
    roles: ['client_director'],
  },

  // ── User Management ─────────────────────────────────
  {
    label: 'Users',
    path: '/users',
    roles: [
      'client_director',
      'institution_admin',
      'admin',
      'principal',
      'hod',
      'staff',
    ],
  },

  // ── Academic Structure ──────────────────────────────
  {
    label: 'Academic Years',
    path: '/academic/years',
    roles: ['client_director', 'institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Structure',
    path: '/academic/structure',
    roles: ['client_director', 'institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Subjects',
    path: '/academic/subjects',
    roles: ['client_director', 'institution_admin', 'admin', 'principal', 'hod', 'teacher'],
  },
  {
    label: 'Subject Groups',
    path: '/academic/subject-groups',
    roles: ['client_director', 'institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Teacher Assignments',
    path: '/academic/assignments',
    roles: ['client_director', 'institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Enrollments',
    path: '/academic/enrollments',
    roles: ['client_director', 'institution_admin', 'admin', 'principal'],
  },

  // ── Configuration ───────────────────────────────────
  {
    label: 'Configuration',
    path: '/config/keys',
    roles: ['client_director', 'institution_admin', 'admin'],
  },
  {
    label: 'Config Audit',
    path: '/config/audit',
    roles: ['client_director', 'institution_admin', 'admin'],
  },

  // ── Fees ────────────────────────────────────────────
  {
    label: 'Fee Types',
    path: '/fees/types',
    roles: ['client_director', 'institution_admin', 'admin'],
  },
  {
    label: 'Fee Assignments',
    path: '/fees/assignments',
    roles: [
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
    roles: ['client_director', 'institution_admin', 'admin', 'principal', 'hod', 'student'],
  },

  // ── Homework & Grading ──────────────────────────────
  {
    label: 'Homework',
    path: '/homework',
    roles: ['client_director', 'institution_admin', 'admin', 'principal', 'hod', 'teacher'],
  },
  {
    label: 'Submissions',
    path: '/homework/submissions',
    roles: ['client_director', 'institution_admin', 'admin', 'principal', 'hod', 'teacher'],
  },
  {
    label: 'Grades',
    path: '/homework/grades',
    roles: ['client_director', 'institution_admin', 'admin', 'principal', 'hod', 'teacher'],
  },

  // ── Student Views ───────────────────────────────────
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
