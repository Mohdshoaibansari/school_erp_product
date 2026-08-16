import { describe, expect, it } from 'vitest';
import { resolveDefaultInstitution } from '../tenant';

describe('resolveDefaultInstitution (R4)', () => {
  const institutions = [{ id: 'a' }, { id: 'b' }];

  it('prefers the last-used institution when present', () => {
    expect(resolveDefaultInstitution(institutions, 'b')).toBe('b');
  });

  it('falls back to the first institution when none is remembered', () => {
    expect(resolveDefaultInstitution(institutions, null)).toBe('a');
  });

  it('falls back to the first institution when last-used is unknown', () => {
    expect(resolveDefaultInstitution(institutions, 'zzz')).toBe('a');
  });

  it('returns null for an empty list', () => {
    expect(resolveDefaultInstitution([], 'a')).toBeNull();
  });
});
