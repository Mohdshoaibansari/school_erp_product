import { describe, expect, it } from 'vitest';
import { hasRole, isRole } from '../roles';
import { NAV_ITEMS, navItemsForRoles, rolesForPath } from '../navConfig';

describe('access / roles + navConfig (REQ-SHELL-03, REQ-SHELL-10)', () => {
  it('hasRole works for the three management roles', () => {
    expect(hasRole(['platform_owner'], 'platform_owner')).toBe(true);
    expect(hasRole(['platform_owner'], 'client_director')).toBe(false);
  });

  it('isRole only accepts management roles', () => {
    expect(isRole('institution_admin')).toBe(true);
    expect(isRole('teacher')).toBe(false);
  });

  it('maps P1 modules to their required roles', () => {
    expect(rolesForPath('/platform/clients')).toEqual(['platform_owner']);
    expect(rolesForPath('/platform/clients/abc123')).toEqual(['platform_owner']);
    expect(rolesForPath('/institutions')).toEqual(['client_director']);
    expect(rolesForPath('/users')).toEqual(['client_director', 'institution_admin']);
  });

  it('returns an empty role set for unrestricted paths', () => {
    expect(rolesForPath('/account/change-password')).toEqual([]);
  });

  it('filters nav items by role', () => {
    const po = navItemsForRoles(['platform_owner']).map((i) => i.path);
    expect(po).toContain('/platform/clients');
    expect(po).not.toContain('/users');

    const admin = navItemsForRoles(['institution_admin']).map((i) => i.path);
    expect(admin).toEqual([
      '/users',
      '/academic/years',
      '/academic/subjects',
      '/academic/subject-groups',
      '/config/keys',
      '/config/audit',
      '/fees/types',
      '/fees/assignments',
      '/fees/payments',
      '/homework',
      '/homework/grades',
    ]);

    const cd = navItemsForRoles(['client_director']).map((i) => i.path);
    expect(cd).toEqual(['/institutions', '/users']);
  });

  it('has no Roles & Permissions nav entry (REQ-FE-USR-06)', () => {
    const labels = NAV_ITEMS.map((i) => i.label.toLowerCase());
    expect(labels).not.toContain('roles');
    expect(labels).not.toContain('permissions');
  });
});
