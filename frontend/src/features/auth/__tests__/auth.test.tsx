import { describe, expect, it } from 'vitest';
import type { ReactNode } from 'react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { server } from '../../../test/server';
import { mintToken, renderWithProviders } from '../../../test/testUtils';
import Login from '../Login';
import Activate from '../Activate';
import OtpVerify from '../OtpVerify';
import ResetPassword from '../ResetPassword';

function AuthRoutes({ children }: { children: ReactNode }) {
  return (
    <Routes>
      <Route path="/login" element={children} />
      <Route path="/" element={<div>shell-home</div>} />
    </Routes>
  );
}

describe('auth screens (REQ-FE-AUTH-*)', () => {
  it('login success loads the shell; failure shows inline error without route change (REQ-FE-AUTH-01)', async () => {
    server.use(
      http.post('/api/auth/login', async ({ request }) => {
        const body = (await request.json()) as { password: string };
        if (body.password === 'good') {
          return HttpResponse.json({
            access_token: mintToken({ sub: 'u1', is_platform_owner: true }),
            refresh_token: 'r',
            token_type: 'bearer',
            expires_in: 3600,
            is_platform_owner: true,
            user_tier: null,
            client_id: null,
          });
        }
        return HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 });
      }),
    );

    const { unmount } = renderWithProviders(
      <AuthRoutes>
        <Login />
      </AuthRoutes>,
      { route: '/login', claims: null },
    );

    // Failure path
    await userEvent.type(screen.getByTestId('login-email'), 'a@b.c');
    await userEvent.type(screen.getByTestId('login-password'), 'bad');
    await userEvent.click(screen.getByTestId('login-submit'));

    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument();
    expect(screen.queryByText('shell-home')).not.toBeInTheDocument();

    // Success path
    unmount();
    renderWithProviders(
      <AuthRoutes>
        <Login />
      </AuthRoutes>,
      { route: '/login', claims: null },
    );
    await userEvent.type(screen.getByTestId('login-email'), 'a@b.c');
    await userEvent.type(screen.getByTestId('login-password'), 'good');
    await userEvent.click(screen.getByTestId('login-submit'));

    expect(await screen.findByText('shell-home')).toBeInTheDocument();
  });

  it('activation redirects to /login (REQ-FE-AUTH-02, R3)', async () => {
    server.use(
      http.post('/api/auth/activate', () =>
        HttpResponse.json({
          message: 'activated',
          user_id: 'u1',
          user_tier: 'institution',
          client_slug: 'acme',
        }),
      ),
    );

    renderWithProviders(
      <Routes>
        <Route path="/activate" element={<Activate />} />
        <Route path="/login" element={<div>login-page</div>} />
      </Routes>,
      { route: '/activate?token=invite123', claims: null },
    );

    await userEvent.type(screen.getByTestId('activate-password'), 'pass1234');
    await userEvent.type(screen.getByTestId('activate-confirm'), 'pass1234');
    await userEvent.click(screen.getByText('Activate'));

    expect(await screen.findByText('login-page')).toBeInTheDocument();
  });

  it('OTP request/verify with error and re-request (REQ-FE-AUTH-03)', async () => {
    server.use(
      http.post('/api/auth/otp/request', () => HttpResponse.json({ message: 'sent' })),
      http.post('/api/auth/otp/verify', async ({ request }) => {
        const body = (await request.json()) as { token: string };
        if (body.token === '123456') {
          return HttpResponse.json({
            access_token: 'x',
            refresh_token: 'y',
            token_type: 'bearer',
            expires_in: 3600,
          });
        }
        return HttpResponse.json({ detail: 'Invalid or expired code' }, { status: 400 });
      }),
    );

    renderWithProviders(<OtpVerify />, { claims: null });

    await userEvent.type(screen.getByTestId('otp-email'), 'a@b.c');
    await userEvent.click(screen.getByText('Send code'));
    expect(await screen.findByTestId('otp-input')).toBeInTheDocument();

    // wrong code → inline error + re-request available
    await userEvent.type(screen.getByTestId('otp-input'), '000000');
    await userEvent.click(screen.getByText('Verify'));
    expect(await screen.findByText('Invalid or expired code')).toBeInTheDocument();
    expect(screen.getByText('Re-send code')).toBeInTheDocument();

    // correct code → done
    await userEvent.clear(screen.getByTestId('otp-input'));
    await userEvent.type(screen.getByTestId('otp-input'), '123456');
    await userEvent.click(screen.getByText('Verify'));
    expect(await screen.findByText('Verified')).toBeInTheDocument();
  });

  it('password reset ends at login with a success state (REQ-FE-AUTH-04)', async () => {
    server.use(
      http.post('/api/auth/password/reset/confirm', () =>
        HttpResponse.json({ message: 'ok' }),
      ),
    );

    renderWithProviders(
      <Routes>
        <Route path="/password/reset" element={<ResetPassword />} />
        <Route path="/login" element={<div>login-page</div>} />
      </Routes>,
      { route: '/password/reset?token=reset123', claims: null },
    );

    await userEvent.type(screen.getByTestId('reset-password'), 'newpass1');
    await userEvent.type(screen.getByTestId('reset-confirm'), 'newpass1');
    await userEvent.click(screen.getByText('Set password'));

    expect(await screen.findByText('login-page')).toBeInTheDocument();
  });
});
