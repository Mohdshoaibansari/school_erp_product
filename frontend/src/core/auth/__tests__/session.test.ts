import { describe, expect, it } from 'vitest';
import { buildSessionUser, decodeJwt, deriveRoles } from '../session';
import { mintToken } from '../../../test/testUtils';

describe('session', () => {
  it('derives platform_owner from the is_platform_owner claim', () => {
    expect(deriveRoles({ is_platform_owner: true })).toEqual(['platform_owner']);
  });

  it('derives client_director from user_tier=client_leadership', () => {
    expect(deriveRoles({ user_tier: 'client_leadership' })).toEqual(['client_director']);
  });

  it('derives institution_admin from user_tier=institution', () => {
    expect(deriveRoles({ user_tier: 'institution' })).toEqual(['institution_admin']);
  });

  it('prefers an explicit roles array when present', () => {
    expect(deriveRoles({ roles: ['client_director'], user_tier: 'institution' })).toEqual([
      'client_director',
    ]);
  });

  it('decodes a JWT payload', () => {
    const claims = { sub: 'u1', is_platform_owner: true, client_id: 'c1' };
    const token = mintToken(claims);
    expect(decodeJwt(token)).toMatchObject({ sub: 'u1', is_platform_owner: true });
  });

  it('builds a session user with roles and tenant ids', () => {
    const user = buildSessionUser({
      sub: 'u1',
      user_tier: 'institution',
      client_id: 'c1',
      institution_id: 'i1',
    });
    expect(user).not.toBeNull();
    expect(user?.roles).toEqual(['institution_admin']);
    expect(user?.clientId).toBe('c1');
    expect(user?.institutionId).toBe('i1');
  });

  it('returns null when the token has no subject', () => {
    expect(buildSessionUser({})).toBeNull();
  });
});
