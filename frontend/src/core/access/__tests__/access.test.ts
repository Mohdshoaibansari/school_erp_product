import { describe, expect, it } from 'vitest';
import { hasRole, isRole } from '../roles';
import { NAV_ITEMS, navItemsForRoles, rolesForPath } from '../navConfig';

describe('access / roles + navConfig (REQ-SHELL-03, REQ-SHELL-10)', () => {
  it('hasRole works for management and institution roles', () => {
    expect(hasRole(['platform_owner'], 'platform_owner')).toBe(true);
    expect(hasRole(['platform_owner'], 'client_director')).toBe(false);
    expect(hasRole(['teacher'], 'teacher')).toBe(true);
  });

  it('isRole accepts all platform roles', () => {
    expect(isRole('institution_admin')).toBe(true);
    expect(isRole('teacher')).toBe(true);
    expect(isRole('student')).toBe(true);
    expect(isRole('unknown_role')).toBe(false);
  });

  it('maps modules to their required roles', () => {
    expect(rolesForPath('/platform/clients')).toEqual(['platform_owner']);
    expect(rolesForPath('/platform/clients/abc123')).toEqual(['platform_owner']);
    expect(rolesForPath('/institutions')).toEqual(['client_director']);
    expect(rolesForPath('/users')).toEqual([
      'client_director', 'institution_admin', 'admin', 'principal', 'hod', 'staff',
    ]);
    expect(rolesForPath('/homework')).toEqual([
      'client_director', 'institution_admin', 'admin', 'principal', 'hod', 'teacher',
    ]);
  });

  it('returns an empty role set for unrestricted paths', () => {
    expect(rolesForPath('/account/change-password')).toEqual([]);
  });

  it('filters nav items by role', () => {
    const po = navItemsForRoles(['platform_owner']).map((i) => i.path);
    expect(po).toContain('/platform/clients');
    expect(po).toContain('/platform/institution-types');
    expect(po).toContain('/platform/ownership-transfers');
    expect(po).not.toContain('/institutions');
    expect(po).not.toContain('/users');
    expect(po).not.toContain('/academic/years');
    expect(po).not.toContain('/config/keys');
    expect(po).not.toContain('/fees/types');
    expect(po).not.toContain('/homework');

    const cd = navItemsForRoles(['client_director']).map((i) => i.path);
    expect(cd).toContain('/institutions');
    expect(cd).toContain('/users');
    expect(cd).toContain('/academic/years');
    expect(cd).toContain('/config/keys');
    expect(cd).toContain('/fees/types');
    expect(cd).toContain('/homework');
    expect(cd).not.toContain('/platform/clients');

    const admin = navItemsForRoles(['institution_admin']).map((i) => i.path);
    expect(admin).toContain('/users');
    expect(admin).toContain('/academic/years');
    expect(admin).toContain('/config/keys');
    expect(admin).toContain('/fees/types');
    expect(admin).toContain('/homework');
    expect(admin).not.toContain('/institutions');

    const teacher = navItemsForRoles(['teacher']).map((i) => i.path);
    expect(teacher).toContain('/homework');
    expect(teacher).toContain('/homework/grades');
    expect(teacher).toContain('/academic/subjects');
    expect(teacher).not.toContain('/users');
    expect(teacher).not.toContain('/config/keys');

    const student = navItemsForRoles(['student']).map((i) => i.path);
    expect(student).toContain('/student/homework');
    expect(student).toContain('/student/grades');
    expect(student).toContain('/student/fees');
    expect(student).toContain('/fees/assignments');
    expect(student).not.toContain('/users');

    const principal = navItemsForRoles(['principal']).map((i) => i.path);
    expect(principal).toContain('/users');
    expect(principal).toContain('/academic/years');
    expect(principal).toContain('/fees/assignments');
    expect(principal).toContain('/homework');
    expect(principal).not.toContain('/config/keys');
    expect(principal).not.toContain('/fees/types');
  });

  it('has no Roles & Permissions nav entry (REQ-FE-USR-06)', () => {
    const labels = NAV_ITEMS.map((i) => i.label.toLowerCase());
    expect(labels).not.toContain('roles');
    expect(labels).not.toContain('permissions');
  });
});
