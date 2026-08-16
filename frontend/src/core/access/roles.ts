/**
 * Management roles only (D5, REQ-SHELL-10). Role gating is derived from the
 * JWT claims; no C-04 authorization routes are consumed.
 */
export const ROLES = [
  'platform_owner',
  'client_director',
  'institution_admin',
] as const;

export type Role = (typeof ROLES)[number];

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value);
}

export function hasRole(roles: readonly string[], role: Role): boolean {
  return roles.includes(role);
}

/** Human-readable labels for UI display. */
export const ROLE_LABELS: Record<Role, string> = {
  platform_owner: 'Platform Owner',
  client_director: 'Client Director',
  institution_admin: 'Institution Admin',
};
