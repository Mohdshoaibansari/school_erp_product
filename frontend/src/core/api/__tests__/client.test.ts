import { afterEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/server';
import { api } from '../client';
import { sessionEvents } from '../tokenStore';

const defaultOnExpired = sessionEvents.onExpired;

afterEach(() => {
  sessionEvents.onExpired = defaultOnExpired;
  window.sessionStorage.clear();
});

describe('api client request interceptor (REQ-SHELL-08)', () => {
  it('attaches the bearer header when a token is present and omits it otherwise', async () => {
    const seen: string[] = [];
    server.use(
      http.get('/api/v1/ping', ({ request }) => {
        seen.push(request.headers.get('authorization') ?? '');
        return HttpResponse.json({ ok: true });
      }),
    );

    window.sessionStorage.clear();
    await api.get('/api/v1/ping');

    window.sessionStorage.setItem('erp.access_token', 'abc123');
    await api.get('/api/v1/ping');

    expect(seen[0]).toBe('');
    expect(seen[1]).toBe('Bearer abc123');
  });
});

describe('api client response interceptor', () => {
  it('single-flight refresh then retries once (REQ-SHELL-06)', async () => {
    let refreshCalls = 0;
    server.use(
      http.post('/api/auth/refresh', () => {
        refreshCalls += 1;
        return HttpResponse.json({
          access_token: 'new-token',
          refresh_token: 'new-refresh',
          token_type: 'bearer',
          expires_in: 3600,
        });
      }),
      http.get('/api/v1/protected', ({ request }) => {
        if (request.headers.get('authorization') === 'Bearer new-token') {
          return HttpResponse.json({ ok: true });
        }
        return HttpResponse.json({ detail: 'unauthorized' }, { status: 401 });
      }),
    );

    window.sessionStorage.setItem('erp.access_token', 'expired');
    window.sessionStorage.setItem('erp.refresh_token', 'refresh');

    const results = await Promise.all([
      api.get('/api/v1/protected'),
      api.get('/api/v1/protected'),
      api.get('/api/v1/protected'),
    ]);

    expect(refreshCalls).toBe(1);
    expect(results.map((r) => r.data)).toEqual([{ ok: true }, { ok: true }, { ok: true }]);
  });

  it('clears tokens and redirects when refresh returns 401 (REQ-SHELL-06)', async () => {
    const onExpired = vi.fn();
    sessionEvents.onExpired = onExpired;

    server.use(
      http.post('/api/auth/refresh', () =>
        HttpResponse.json({ detail: 'invalid refresh token' }, { status: 401 }),
      ),
      http.get('/api/v1/protected', () =>
        HttpResponse.json({ detail: 'unauthorized' }, { status: 401 }),
      ),
    );

    window.sessionStorage.setItem('erp.access_token', 'expired');
    window.sessionStorage.setItem('erp.refresh_token', 'refresh');

    await expect(api.get('/api/v1/protected')).rejects.toBeTruthy();
    expect(onExpired).toHaveBeenCalledTimes(1);
    expect(window.sessionStorage.getItem('erp.access_token')).toBeNull();
  });

  it('does not refresh-loop on auth-route 401 (REQ-FE-AUTH-07)', async () => {
    let refreshCalls = 0;
    const onExpired = vi.fn();
    sessionEvents.onExpired = onExpired;

    server.use(
      http.post('/api/auth/refresh', () => {
        refreshCalls += 1;
        return HttpResponse.json({ access_token: 'x', refresh_token: 'x' });
      }),
      http.post('/api/auth/login', () =>
        HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 }),
      ),
    );

    await expect(
      api.post('/api/auth/login', { email: 'a@b.c', password: 'wrong' }),
    ).rejects.toBeTruthy();

    expect(refreshCalls).toBe(0);
    expect(onExpired).not.toHaveBeenCalled();
  });

  it('does not redirect on 403 and flags forbidden (REQ-SHELL-07)', async () => {
    const onExpired = vi.fn();
    sessionEvents.onExpired = onExpired;

    server.use(
      http.get('/api/v1/blocked', () =>
        HttpResponse.json({ detail: 'Permission denied' }, { status: 403 }),
      ),
    );

    const err = await api.get('/api/v1/blocked').catch((e: unknown) => e);
    expect(onExpired).not.toHaveBeenCalled();
    expect(err).toMatchObject({ status: 403, forbidden: true });
  });
});
