import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { renderWithProviders } from '../../../test/testUtils';
import { RequireRole } from '../RequireRole';
import type { JwtClaims } from '../../auth/session';

const poClaims: JwtClaims & { sub: string } = {
  sub: 'po1',
  roles: ['platform_owner'],
  is_platform_owner: true,
  client_id: null,
  institution_id: null,
};
const cdClaims: JwtClaims & { sub: string } = {
  sub: 'cd1',
  roles: ['client_director'],
  user_tier: 'client_leadership',
  client_id: 'c1',
  institution_id: null,
};
const adminClaims: JwtClaims & { sub: string } = {
  sub: 'a1',
  roles: ['institution_admin'],
  user_tier: 'institution',
  client_id: 'c1',
  institution_id: 'i1',
};

const cases: Array<{ role: string; claims: JwtClaims & { sub: string }; path: string; allowed: boolean }> = [
  { role: 'platform_owner', claims: poClaims, path: '/platform/clients', allowed: true },
  { role: 'platform_owner', claims: poClaims, path: '/platform/institution-types', allowed: true },
  { role: 'platform_owner', claims: poClaims, path: '/platform/ownership-transfers', allowed: true },
  { role: 'platform_owner', claims: poClaims, path: '/institutions', allowed: false },
  { role: 'platform_owner', claims: poClaims, path: '/users', allowed: false },
  { role: 'client_director', claims: cdClaims, path: '/institutions', allowed: true },
  { role: 'client_director', claims: cdClaims, path: '/users', allowed: true },
  { role: 'client_director', claims: cdClaims, path: '/platform/clients', allowed: false },
  { role: 'institution_admin', claims: adminClaims, path: '/users', allowed: true },
  { role: 'institution_admin', claims: adminClaims, path: '/institutions', allowed: false },
  { role: 'institution_admin', claims: adminClaims, path: '/platform/clients', allowed: false },
  { role: 'institution_admin', claims: adminClaims, path: '/fees/types', allowed: true },
  { role: 'institution_admin', claims: adminClaims, path: '/fees/assignments', allowed: true },
  { role: 'institution_admin', claims: adminClaims, path: '/fees/payments', allowed: true },
  { role: 'institution_admin', claims: adminClaims, path: '/homework', allowed: true },
  { role: 'institution_admin', claims: adminClaims, path: '/homework/grades', allowed: true },
  { role: 'platform_owner', claims: poClaims, path: '/fees/types', allowed: false },
  { role: 'client_director', claims: cdClaims, path: '/homework', allowed: false },
];

describe('role fixture matrix (P1-AC-1, REQ-SHELL-03/10)', () => {
  it.each(cases)('$role at $path → allowed = $allowed', async ({ claims, path, allowed }) => {
    renderWithProviders(
      <Routes>
        <Route element={<RequireRole />}>
          <Route path={path} element={<div>allowed-content</div>} />
        </Route>
      </Routes>,
      { route: path, claims },
    );

    if (allowed) {
      expect(await screen.findByText('allowed-content')).toBeInTheDocument();
    } else {
      expect(await screen.findByText("You don't have permission")).toBeInTheDocument();
    }
  });
});
