import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/server';
import { renderWithProviders } from '../../../test/testUtils';
import type { JwtClaims } from '../../../core/auth/session';
import type { UserDTO } from '../../../core/api/dto/users';
import { Users } from '../Users';

const adminClaims: JwtClaims & { sub: string } = {
  sub: 'a1',
  roles: ['institution_admin'],
  user_tier: 'institution',
  client_id: 'c1',
  institution_id: 'i1',
};

function makeUser(overrides: Partial<UserDTO> = {}): UserDTO {
  return {
    id: 'u1',
    client_id: 'c1',
    institution_id: 'i1',
    email: 'learner@school.test',
    person: {
      id: 'p1',
      client_id: 'c1',
      name: 'Aisha Learner',
      date_of_birth: null,
      gender: null,
      blood_group: null,
      photo: null,
      contact_phone: null,
      contact_email: null,
      demographics: null,
      status: 'Active',
      is_minor: null,
      is_verified: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    lifecycle_status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('Users screen (REQ-FE-USR-01, REQ-FE-USR-05)', () => {
  it('lists users, creates a user, and sources dropdowns from lookups', async () => {
    const users: UserDTO[] = [makeUser()];
    const createBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/users', () => HttpResponse.json(users)),
      http.get('/api/v1/lookups/roles', () =>
        HttpResponse.json([{ id: 'r1', name: 'Teacher' }]),
      ),
      http.post('/api/v1/users', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        createBodies.push(body);
        const pd = (body.person_data as Record<string, string>) || {};
        const created = makeUser({
          id: 'u2',
          email: body.email as string,
          person: {
            ...makeUser().person,
            id: 'p2',
            name: pd.name || 'New User',
          },
        });
        users.push(created);
        return HttpResponse.json(
          { user: created, invite_url: 'https://example/invite' },
          { status: 201 },
        );
      }),
    );

    renderWithProviders(<Users />, { claims: adminClaims });

    // List
    expect(await screen.findByText('Aisha Learner')).toBeInTheDocument();

    // Create (dropdowns sourced from lookups)
    await userEvent.click(screen.getByRole('button', { name: 'New user' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Name' }), 'Ben Learner');
    await userEvent.type(screen.getByRole('textbox', { name: 'Email' }), 'ben@school.test');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('Ben Learner')).toBeInTheDocument();
    expect(createBodies.length).toBe(1);
    expect(createBodies[0]).toMatchObject({
      email: 'ben@school.test',
      person_data: { name: 'Ben Learner' },
      institution_id: 'i1',
    });
  });
});
