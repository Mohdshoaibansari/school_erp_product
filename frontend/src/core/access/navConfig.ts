import type { Role } from './roles';

export interface NavItem {
  label: string;
  path: string;
  roles: Role[];
  icon?: string;
}

/**
 * Declarative nav → role map (REQ-SHELL-03, REQ-SHELL-10). The sidebar and the
 * route guard both consume this map so a role change cannot desync nav from
 * route protection.
 */
export const NAV_ITEMS: NavItem[] = [
  // ── Platform Owner ──────────────────────────────────
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

  // ── Client Director ─────────────────────────────────
  { label: 'Institutions', path: '/institutions', roles: ['client_director'] },

  // ── Institution Admin / Admin ───────────────────────
  {
    label: 'Users',
    path: '/users',
    roles: ['client_director', 'institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Academic Years',
    path: '/academic/years',
    roles: ['institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Structure',
    path: '/academic/structure',
    roles: ['institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Subjects',
    path: '/academic/subjects',
    roles: ['institution_admin', 'admin', 'principal', 'hod'],
  },
  {
    label: 'Subject Groups',
    path: '/academic/subject-groups',
    roles: ['institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Teacher Assignments',
    path: '/academic/assignments',
    roles: ['institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Enrollments',
    path: '/academic/enrollments',
    roles: ['institution_admin', 'admin', 'principal'],
  },
  {
    label: 'Configuration',
    path: '/config/keys',
    roles: ['institution_admin', 'admin'],
  },
  {
    label: 'Config Audit',
    path: '/config/audit',
    roles: ['institution_admin', 'admin'],
  },

  // ── Fees (admin + finance roles) ────────────────────
  {
    label: 'Fee Types',
    path: '/fees/types',
    roles: ['institution_admin', 'admin'],
  },
  {
    label: 'Fee Assignments',
    path: '/fees/assignments',
    roles: ['institution_admin', 'admin'],
  },
  {
    label: 'Payments',
    path: '/fees/payments',
    roles: ['institution_admin', 'admin'],
  },

  // ── Homework (admin + teacher) ──────────────────────
  {
    label: 'Homework',
    path: '/homework',
    roles: ['institution_admin', 'admin', 'teacher', 'hod'],
  },
  {
    label: 'Grades',
    path: '/homework/grades',
    roles: ['institution_admin', 'admin', 'teacher', 'hod'],
  },

  // ── Student ─────────────────────────────────────────
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

  // ── Parent ──────────────────────────────────────────
  {
    label: 'Child Progress',
    path: '/parent/progress',
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
