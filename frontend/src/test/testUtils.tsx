import type { ReactElement, ReactNode } from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { MemoryRouter } from 'react-router-dom';
import { theme } from '../theme';
import { AuthProvider } from '../core/auth/AuthProvider';
import { TenantProvider } from '../core/context/TenantProvider';
import type { JwtClaims } from '../core/auth/session';

function encodeSegment(value: unknown): string {
  return btoa(JSON.stringify(value))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/** Mint a fake JWT (client-side decode ignores signature). */
export function mintToken(claims: JwtClaims): string {
  return `${encodeSegment({ alg: 'HS256', typ: 'JWT' })}.${encodeSegment(claims)}.signature`;
}

/** Seed a restored session directly into sessionStorage (simulates a reload). */
export function seedSession(claims: JwtClaims & { sub: string }): void {
  window.sessionStorage.setItem('erp.access_token', mintToken(claims));
  window.sessionStorage.setItem('erp.refresh_token', 'refresh-token');
  window.sessionStorage.setItem(
    'erp.session_meta',
    JSON.stringify({
      isPlatformOwner: claims.is_platform_owner ?? null,
      userTier: claims.user_tier ?? null,
      clientId: claims.client_id ?? null,
      institutionId: claims.institution_id ?? null,
    }),
  );
}

export function clearSession(): void {
  window.sessionStorage.clear();
}

export interface RenderOptions {
  route?: string;
  claims?: (JwtClaims & { sub: string }) | null;
}

export function renderWithProviders(ui: ReactElement, options: RenderOptions = {}) {
  const { route = '/', claims = null } = options;
  if (claims) seedSession(claims);

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MantineProvider theme={theme} env="test">
          <MemoryRouter initialEntries={[route]}>
            <AuthProvider>
              <TenantProvider>{children}</TenantProvider>
            </AuthProvider>
          </MemoryRouter>
        </MantineProvider>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper });
}
