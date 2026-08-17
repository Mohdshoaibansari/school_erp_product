import { describe, expect, it } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/server';
import { renderWithProviders } from '../../../test/testUtils';
import type { JwtClaims } from '../../../core/auth/session';
import type { ClientDTO } from '../../../core/api/dto/platform';
import { Clients } from '../Clients';

const poClaims: JwtClaims & { sub: string } = {
  sub: 'po1',
  roles: ['platform_owner'],
  is_platform_owner: true,
  client_id: null,
  institution_id: null,
};

function makeClient(overrides: Partial<ClientDTO> = {}): ClientDTO {
  return {
    id: 'c1',
    slug: 'acme',
    display_name: 'Acme Schools',
    legal_name: 'Acme Schools Ltd',
    legal_entity_type_id: 'le1',
    tax_registration_number: null,
    primary_contact_email: 'ops@acme.test',
    primary_contact_phone: null,
    billing_contact_email: null,
    address_id: null,
    current_lifecycle_status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    archived_at: null,
    ...overrides,
  };
}

describe('Clients screen (REQ-FE-TI-01)', () => {
  it('lists, creates, and transitions clients', async () => {
    const clients: ClientDTO[] = [makeClient()];
    const createBodies: unknown[] = [];
    const transitionBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/platform/clients', () => HttpResponse.json(clients)),
      http.get('/api/v1/lookups/legal-entity-types', () =>
        HttpResponse.json([{ id: 'le1', name: 'Private Limited' }]),
      ),
      http.post('/api/v1/platform/clients', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        createBodies.push(body);
        const created = makeClient({
          id: 'c2',
          slug: body.slug as string,
          display_name: body.display_name as string,
        });
        clients.push(created);
        return HttpResponse.json(created, { status: 201 });
      }),
      http.post('/api/v1/platform/clients/:id/transition', async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>;
        transitionBodies.push({ id: params.id, ...body });
        return HttpResponse.json(makeClient({ current_lifecycle_status: body.new_state as string }));
      }),
    );

    renderWithProviders(<Clients />, { claims: poClaims });

    // List
    expect(await screen.findByText('Acme Schools')).toBeInTheDocument();

    // Create
    await userEvent.click(screen.getByTestId('clients-create'));
    await userEvent.type(screen.getByRole('textbox', { name: 'Slug' }), 'north');
    await userEvent.type(screen.getByRole('textbox', { name: 'Display name' }), 'North Schools');
    await userEvent.type(screen.getByRole('textbox', { name: 'Legal name' }), 'North Schools Ltd');
    await userEvent.click(screen.getByRole('combobox', { name: 'Legal entity type' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Private Limited' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Primary contact email' }), 'ops@north.test');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('North Schools')).toBeInTheDocument();
    expect(createBodies.length).toBe(1);
    expect(createBodies[0]).toMatchObject({ slug: 'north', display_name: 'North Schools' });

    // Transition
    await userEvent.click(screen.getAllByRole('button', { name: 'Transition' })[0]);
    const transitionDialog = await screen.findByRole('dialog');
    await userEvent.click(screen.getByRole('combobox', { name: 'New state' }));
    await userEvent.click(await screen.findByRole('option', { name: 'suspended' }));
    await userEvent.click(within(transitionDialog).getByRole('button', { name: 'Transition' }));

    expect(transitionBodies.length).toBe(1);
    expect(transitionBodies[0]).toMatchObject({ id: 'c1', new_state: 'suspended' });
  });
});
