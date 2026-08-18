import type { Role } from '../access/roles';

/** JWT claims the frontend relies on (no signature verification on the client). */
export interface JwtClaims {
  sub?: string;
  email?: string;
  roles?: string[];
  is_platform_owner?: boolean;
  user_tier?: string | null;
  client_id?: string | null;
  institution_id?: string | null;
}

/** Persisted session metadata (survives a tab reload alongside the token). */
export interface SessionMeta {
  isPlatformOwner?: boolean | null;
  userTier?: 'client_leadership' | 'institution' | null;
  clientId?: string | null;
  institutionId?: string | null;
  email?: string | null;
}

export interface SessionUser {
  userId: string;
  email: string | null;
  roles: Role[];
  isPlatformOwner: boolean;
  userTier: 'client_leadership' | 'institution' | null;
  clientId: string | null;
  institutionId: string | null;
}

function base64UrlDecode(segment: string): string {
  const base64 = segment.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new TextDecoder().decode(bytes);
}

export function decodeJwt(token: string): JwtClaims {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return {};
    return JSON.parse(base64UrlDecode(parts[1])) as JwtClaims;
  } catch {
    return {};
  }
}

/**
 * Derive the management roles from the verified backend claims. The backend
 * does not mint a literal `roles` array; it carries `is_platform_owner` and
 * `user_tier`. We still honor a `roles` array if present (future-proofing).
 */
/**
 * Normalize backend role names to frontend role keys.
 * Backend stores some roles capitalized ("Teacher", "Admin") while frontend
 * uses lowercase ("teacher", "admin"). This map handles the mismatch.
 */
const ROLE_NORMALIZE: Record<string, Role> = {
  platform_owner: 'platform_owner',
  client_director: 'client_director',
  institution_admin: 'institution_admin',
  admin: 'admin',
  teacher: 'teacher',
  hod: 'hod',
  principal: 'principal',
  student: 'student',
  parent: 'parent',
  staff: 'staff',
};

function normalizeRole(raw: string): Role | null {
  return ROLE_NORMALIZE[raw.toLowerCase()] ?? null;
}

export function deriveRoles(claims: JwtClaims, meta?: SessionMeta): Role[] {
  // 1. Normalize roles from the JWT roles array (backend DB roles, may be capitalized)
  if (Array.isArray(claims.roles) && claims.roles.length > 0) {
    const normalized = claims.roles
      .map(normalizeRole)
      .filter((r): r is Role => r !== null);
    if (normalized.length > 0) return [...new Set(normalized)];
  }
  // 2. Fallback: derive management roles from tier claims (JWT or stored metadata)
  const roles: Role[] = [];
  if (claims.is_platform_owner || meta?.isPlatformOwner) roles.push('platform_owner');
  const rawTier = claims.user_tier ?? meta?.userTier ?? null;
  if (rawTier === 'client_leadership') roles.push('client_director');
  if (rawTier === 'institution') roles.push('institution_admin');
  return roles;
}

export function buildSessionUser(
  claims: JwtClaims,
  meta: SessionMeta = {},
): SessionUser | null {
  const userId = claims.sub;
  if (!userId) return null;

  const isPlatformOwner =
    claims.is_platform_owner ?? meta.isPlatformOwner ?? false;
  const rawTier = claims.user_tier ?? meta.userTier ?? null;
  const userTier =
    rawTier === 'client_leadership' || rawTier === 'institution'
      ? rawTier
      : null;

  return {
    userId,
    email: claims.email ?? meta.email ?? null,
    roles: deriveRoles(claims, meta),
    isPlatformOwner,
    userTier,
    clientId: claims.client_id ?? meta.clientId ?? null,
    institutionId: claims.institution_id ?? meta.institutionId ?? null,
  };
}
