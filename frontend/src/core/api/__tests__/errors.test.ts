import { describe, expect, it } from 'vitest';
import { ApiError, normalizeApiError } from '../errors';

function fakeAxiosError(status: number, data: unknown, message = 'Request failed') {
  return { isAxiosError: true, message, response: { status, data } };
}

describe('normalizeApiError', () => {
  it('maps a 403 response to a forbidden ApiError (REQ-SHELL-07)', () => {
    const error = normalizeApiError(
      fakeAxiosError(403, { detail: 'Platform Owner privileges required' }),
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error.forbidden).toBe(true);
    expect(error.status).toBe(403);
    expect(error.message).toBe('Platform Owner privileges required');
  });

  it('maps a 422/400 object detail to a non-forbidden ApiError with code', () => {
    const error = normalizeApiError(
      fakeAxiosError(422, { detail: { error: 'slug_taken', slug: 'acme' } }),
    );
    expect(error.forbidden).toBe(false);
    expect(error.code).toBe('slug_taken');
    expect(error.message).toBe('slug_taken');
  });

  it('maps a string detail to a non-forbidden ApiError', () => {
    const error = normalizeApiError(fakeAxiosError(404, { detail: 'Client not found' }));
    expect(error.forbidden).toBe(false);
    expect(error.message).toBe('Client not found');
  });

  it('passes through an existing ApiError unchanged', () => {
    const original = new ApiError(403, 'nope', { forbidden: true });
    expect(normalizeApiError(original)).toBe(original);
  });

  it('handles non-axios errors', () => {
    const error = normalizeApiError(new Error('boom'));
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe('boom');
  });
});
