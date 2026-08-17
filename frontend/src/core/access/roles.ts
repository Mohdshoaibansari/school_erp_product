/**
 * All platform roles (D5, REQ-SHELL-10). Role gating is derived from the JWT
 * claims; no C-04 authorization routes are consumed.
 *
 * Management roles: platform_owner, client_director, institution_admin
 * Institution roles: admin, teacher, hod, principal, student, parent, staff
 */
export const ROLES = [
  'platform_owner',
  'client_director',
  'institution_admin',
  'admin',
  'teacher',
  'hod',
  'principal',
  'student',
  'parent',
  'staff',
] as const;

export type Role = (typeof ROLES)[number];

/** Management-level roles (tenant/platform scope). */
export const MANAGEMENT_ROLES: Role[] = [
  'platform_owner',
  'client_director',
  'institution_admin',
];

/** Institution-level roles (institution scope). */
export const INSTITUTION_ROLES: Role[] = [
  'admin',
  'teacher',
  'hod',
  'principal',
  'student',
  'parent',
  'staff',
];

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value);
}

export function hasRole(roles: readonly string[], role: Role): boolean {
  return roles.includes(role);
}

export function hasAnyRole(roles: readonly string[], ...candidates: Role[]): boolean {
  return candidates.some((r) => roles.includes(r));
}

/** Human-readable labels for UI display. */
export const ROLE_LABELS: Record<Role, string> = {
  platform_owner: 'Platform Owner',
  client_director: 'Client Director',
  institution_admin: 'Institution Admin',
  admin: 'Admin',
  teacher: 'Teacher',
  hod: 'Head of Department',
  principal: 'Principal',
  student: 'Student',
  parent: 'Parent',
  staff: 'Staff',
};
