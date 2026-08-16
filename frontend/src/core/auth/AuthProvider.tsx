import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { authApi } from '../api/auth';
import type { LoginResponse } from '../api/dto/auth';
import {
  readAccessToken,
  readRefreshToken,
  writeTokens,
  clearTokens,
} from '../api/tokenStore';
import { AuthContext, type AuthStatus } from './AuthContext';
import {
  buildSessionUser,
  decodeJwt,
  type SessionMeta,
  type SessionUser,
} from './session';

const META_KEY = 'erp.session_meta';

function readMeta(): SessionMeta {
  try {
    const raw = window.sessionStorage.getItem(META_KEY);
    return raw ? (JSON.parse(raw) as SessionMeta) : {};
  } catch {
    return {};
  }
}

function writeMeta(meta: SessionMeta): void {
  window.sessionStorage.setItem(META_KEY, JSON.stringify(meta));
}

function clearMeta(): void {
  window.sessionStorage.removeItem(META_KEY);
}

function restoreSession(): SessionUser | null {
  const token = readAccessToken();
  if (!token) return null;
  return buildSessionUser(decodeJwt(token), readMeta());
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');

  useEffect(() => {
    setUser(restoreSession());
    setStatus(restoreSession() ? 'authenticated' : 'unauthenticated');
  }, []);

  const signIn = useCallback((response: LoginResponse) => {
    writeTokens(response.access_token, response.refresh_token);

    const meta: SessionMeta = {
      isPlatformOwner: response.is_platform_owner,
      userTier: response.user_tier,
      clientId: response.client_id,
      institutionId: null,
      email: null,
    };
    writeMeta(meta);

    const claims = decodeJwt(response.access_token);
    setUser(
      buildSessionUser(
        { ...claims, email: claims.email },
        { ...meta, email: claims.email },
      ),
    );
    setStatus('authenticated');
  }, []);

  const signOut = useCallback(async () => {
    const refreshToken = readRefreshToken();
    if (refreshToken) {
      try {
        await authApi.logout({ refresh_token: refreshToken });
      } catch {
        // Logout is best-effort; always clear local session.
      }
    }
    clearTokens();
    clearMeta();
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  const value = useMemo(
    () => ({ user, status, signIn, signOut }),
    [user, status, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
