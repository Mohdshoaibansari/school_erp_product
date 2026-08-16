const ACCESS_KEY = 'erp.access_token';
const REFRESH_KEY = 'erp.refresh_token';

export function readAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.sessionStorage.getItem(ACCESS_KEY);
}

export function readRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.sessionStorage.getItem(REFRESH_KEY);
}

export function writeTokens(access: string, refresh: string): void {
  if (typeof window === 'undefined') return;
  window.sessionStorage.setItem(ACCESS_KEY, access);
  if (refresh) {
    window.sessionStorage.setItem(REFRESH_KEY, refresh);
  } else {
    window.sessionStorage.removeItem(REFRESH_KEY);
  }
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return;
  window.sessionStorage.removeItem(ACCESS_KEY);
  window.sessionStorage.removeItem(REFRESH_KEY);
}

/**
 * Cross-cutting session-expiry hook. The response interceptor invokes this on
 * refresh failure (401) so the app can redirect to login. Overridable in tests.
 */
export const sessionEvents = {
  onExpired: (): void => {
    if (typeof window !== 'undefined') {
      window.location.assign('/login');
    }
  },
};
