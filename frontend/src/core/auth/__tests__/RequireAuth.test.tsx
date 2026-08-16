import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes, useLocation } from 'react-router-dom';
import { server } from '../../../test/server';
import { renderWithProviders } from '../../../test/testUtils';
import { RequireAuth } from '../RequireAuth';
import { useSession } from '../useSession';
import type { JwtClaims } from '../session';

const adminClaims: JwtClaims & { sub: string } = {
  sub: 'a1',
  roles: ['institution_admin'],
  user_tier: 'institution',
  client_id: 'c1',
  institution_id: 'i1',
};

function LoginStub() {
  const location = useLocation();
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
  return <div>login-page{from ? `:${from}` : ''}</div>;
}

function LogoutButton() {
  const { signOut } = useSession();
  return <button onClick={() => void signOut()}>logout</button>;
}

describe('RequireAuth (REQ-SHELL-06, P1-AC-4)', () => {
  it('redirects to /login preserving the redirect state when unauthenticated', async () => {
    renderWithProviders(
      <Routes>
        <Route element={<RequireAuth />}>
          <Route path="/users" element={<div>protected-content</div>} />
        </Route>
        <Route path="/login" element={<LoginStub />} />
      </Routes>,
      { route: '/users', claims: null },
    );

    expect(await screen.findByText('login-page:/users')).toBeInTheDocument();
    expect(screen.queryByText('protected-content')).not.toBeInTheDocument();
  });

  it('renders protected children for an authenticated session', async () => {
    renderWithProviders(
      <Routes>
        <Route element={<RequireAuth />}>
          <Route path="/users" element={<div>protected-content</div>} />
        </Route>
      </Routes>,
      { route: '/users', claims: adminClaims },
    );

    expect(await screen.findByText('protected-content')).toBeInTheDocument();
  });

  it('logout clears the session and returns to login (REQ-FE-AUTH-06)', async () => {
    server.use(
      http.post('/api/auth/logout', () => HttpResponse.json({ message: 'ok' })),
    );

    renderWithProviders(
      <Routes>
        <Route element={<RequireAuth />}>
          <Route
            path="/users"
            element={
              <>
                <div>protected-content</div>
                <LogoutButton />
              </>
            }
          />
        </Route>
        <Route path="/login" element={<LoginStub />} />
      </Routes>,
      { route: '/users', claims: adminClaims },
    );

    expect(await screen.findByText('protected-content')).toBeInTheDocument();
    await userEvent.click(screen.getByText('logout'));

    expect(await screen.findByText(/^login-page/)).toBeInTheDocument();
    expect(window.sessionStorage.getItem('erp.access_token')).toBeNull();
  });
});
