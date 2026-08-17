import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/server';
import { renderWithProviders } from '../../../test/testUtils';
import type { JwtClaims } from '../../../core/auth/session';
import { ConfigKeys } from '../ConfigKeys';
import { ConfigAudit } from '../ConfigAudit';

const adminClaims: JwtClaims & { sub: string } = {
  sub: 'a1',
  roles: ['institution_admin'],
  user_tier: 'institution',
  client_id: 'c1',
  institution_id: 'i1',
};

function makeKey(overrides: Record<string, unknown> = {}) {
  return {
    id: 'k1',
    key: 'homework.lateSubmissionPolicy',
    type: 'string',
    default_value: 'reject',
    merge_strategy: 'replace',
    category: 'Academic',
    module: 'homework',
    description: 'How late submissions are handled.',
    is_feature_toggle: false,
    is_deprecated: false,
    deprecated_at: null,
    replacement_key: null,
    allowed_values: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('ConfigKeys (REQ-FE-CFG-01/02/04)', () => {
  it('browses keys, edits an institution value type-aware, and shows resolved source', async () => {
    const postBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/config/keys', () =>
        HttpResponse.json({
          total: 1,
          page: 1,
          page_size: 200,
          items: [makeKey()],
        }),
      ),
      http.get('/api/v1/config/values', () =>
        HttpResponse.json({ total: 0, page: 1, page_size: 200, items: [] }),
      ),
      http.get('/api/v1/config/resolve/:keyName', () =>
        HttpResponse.json({
          key: 'homework.lateSubmissionPolicy',
          resolved_value: 'reject',
          source_scope: 'platform:default',
        }),
      ),
      http.post('/api/v1/config/values', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        postBodies.push(body);
        return HttpResponse.json(
          {
            id: 'v1',
            key_id: 'k1',
            scope_type: 'institution',
            scope_id: 'i1',
            client_id: null,
            institution_id: 'i1',
            value: body.value,
            created_at: '2026-01-02T00:00:00Z',
            updated_at: '2026-01-02T00:00:00Z',
            updated_by: 'a1',
          },
          { status: 201 },
        );
      }),
    );

    renderWithProviders(<ConfigKeys />, { claims: adminClaims });

    // Browse keys (all keys listed, none hidden)
    expect(
      await screen.findByText('homework.lateSubmissionPolicy'),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Edit value' }));

    // Resolved (effective) value + source scope
    expect(
      await screen.findByText(/Effective value: reject \(source: platform:default\)/),
    ).toBeInTheDocument();

    // Type-aware string input
    const input = screen.getByRole('textbox', { name: 'Value' });
    await userEvent.clear(input);
    await userEvent.type(input, 'review');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(postBodies.length).toBe(1);
    expect(postBodies[0]).toMatchObject({
      key_id: 'k1',
      scope_type: 'institution',
      scope_id: 'i1',
      value: 'review',
    });
  });

  it('surfaces a backend validation error as a friendly message without hiding the key', async () => {
    server.use(
      http.get('/api/v1/config/keys', () =>
        HttpResponse.json({
          total: 1,
          page: 1,
          page_size: 200,
          items: [makeKey()],
        }),
      ),
      http.get('/api/v1/config/values', () =>
        HttpResponse.json({ total: 0, page: 1, page_size: 200, items: [] }),
      ),
      http.get('/api/v1/config/resolve/:keyName', () =>
        HttpResponse.json({
          key: 'homework.lateSubmissionPolicy',
          resolved_value: 'reject',
          source_scope: 'platform:default',
        }),
      ),
      http.post('/api/v1/config/values', () =>
        HttpResponse.json(
          { detail: 'Value violates allowed values' },
          { status: 422 },
        ),
      ),
    );

    renderWithProviders(<ConfigKeys />, { claims: adminClaims });

    await screen.findByText('homework.lateSubmissionPolicy');
    await userEvent.click(screen.getByRole('button', { name: 'Edit value' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Value' }), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    // Friendly error surfaced, key remains visible (never pre-hidden by the UI)
    expect(await screen.findByText('Value violates allowed values')).toBeInTheDocument();
    expect(screen.getByText('homework.lateSubmissionPolicy')).toBeInTheDocument();
  });

  it('edits a boolean key with a switch input', async () => {
    const patchBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/config/keys', () =>
        HttpResponse.json({
          total: 1,
          page: 1,
          page_size: 200,
          items: [makeKey({ id: 'k2', key: 'homework.enableGrading', type: 'boolean', default_value: false })],
        }),
      ),
      http.get('/api/v1/config/values', () =>
        HttpResponse.json({
          total: 1,
          page: 1,
          page_size: 200,
          items: [
            {
              id: 'v2',
              key_id: 'k2',
              scope_type: 'institution',
              scope_id: 'i1',
              client_id: null,
              institution_id: 'i1',
              value: false,
              created_at: '2026-01-02T00:00:00Z',
              updated_at: '2026-01-02T00:00:00Z',
              updated_by: 'a1',
            },
          ],
        }),
      ),
      http.get('/api/v1/config/resolve/:keyName', () =>
        HttpResponse.json({
          key: 'homework.enableGrading',
          resolved_value: false,
          source_scope: 'institution:i1',
        }),
      ),
      http.patch('/api/v1/config/values/:id', async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>;
        patchBodies.push({ id: params.id, ...body });
        return HttpResponse.json({ id: params.id as string, value: body.value });
      }),
    );

    renderWithProviders(<ConfigKeys />, { claims: adminClaims });

    await screen.findByText('homework.enableGrading');
    await userEvent.click(screen.getByRole('button', { name: 'Edit value' }));

    const toggle = await screen.findByRole('switch', { name: 'Value' });
    await userEvent.click(toggle);
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(patchBodies.length).toBe(1);
    expect(patchBodies[0]).toMatchObject({ id: 'v2', value: true });
  });
});

describe('ConfigAudit (REQ-FE-CFG-03)', () => {
  it('renders audit rows with actor, action, and timestamp', async () => {
    server.use(
      http.get('/api/v1/config/audit', () =>
        HttpResponse.json({
          total: 1,
          page: 1,
          page_size: 200,
          items: [
            {
              id: 'aud1',
              key_id: 'k1',
              scope_type: 'institution',
              scope_id: 'i1',
              action: 'update',
              actor_user_id: 'a1',
              actor_role: 'institution_admin',
              timestamp: '2026-01-15T12:00:00Z',
            },
          ],
        }),
      ),
      http.get('/api/v1/config/keys', () =>
        HttpResponse.json({
          total: 1,
          page: 1,
          page_size: 200,
          items: [makeKey()],
        }),
      ),
    );

    renderWithProviders(<ConfigAudit />, { claims: adminClaims });

    expect(await screen.findByText('update')).toBeInTheDocument();
    expect(screen.getByText('institution_admin')).toBeInTheDocument();
    expect(screen.getByText('homework.lateSubmissionPolicy')).toBeInTheDocument();
  });
});
