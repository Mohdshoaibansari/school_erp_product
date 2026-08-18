import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/server';
import { renderWithProviders } from '../../../test/testUtils';
import type { JwtClaims } from '../../../core/auth/session';
import type { UserDTO } from '../../../core/api/dto/users';
import { TeacherAssignments } from '../TeacherAssignments';
import { Enrollments } from '../Enrollments';

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
    email: 'teacher@school.test',
    person: {
      id: 'p1',
      client_id: 'c1',
      name: 'Aisha Teacher',
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

describe('TeacherAssignments (REQ-FE-AC-05)', () => {
  it('lists, creates, and removes teacher assignments', async () => {
    const assignments = [
      {
        id: 'a1',
        academic_year_id: 'y1',
        teacher_id: 'u1',
        section_id: 's1',
        subject_id: 'sub1',
        status: 'active',
      },
    ];
    const createBodies: unknown[] = [];
    const deleted: string[] = [];

    server.use(
      http.get('/api/v1/teacher-assignments', () =>
        HttpResponse.json(assignments),
      ),
      http.get('/api/v1/subjects', () =>
        HttpResponse.json([
          { id: 'sub1', academic_year_id: 'y1', name: 'Mathematics', code: 'MATH101', sort_order: 1 },
        ]),
      ),
      http.get('/api/v1/users', () => HttpResponse.json([makeUser()])),
      http.post('/api/v1/teacher-assignments', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        createBodies.push(body);
        const created = {
          id: 'a2',
          academic_year_id: 'y1',
          teacher_id: body.teacher_id as string,
          section_id: body.section_id as string,
          subject_id: body.subject_id as string,
          status: 'active',
        };
        assignments.push(created);
        return HttpResponse.json(created, { status: 201 });
      }),
      http.delete('/api/v1/teacher-assignments/:id', ({ params }) => {
        deleted.push(params.id as string);
        return new HttpResponse(null, { status: 204 });
      }),
    );

    renderWithProviders(
      <TeacherAssignments sectionId="s1" academicYearId="y1" />,
      { claims: adminClaims },
    );

    // List (names resolved from lookups)
    expect(await screen.findByText('Aisha Teacher')).toBeInTheDocument();
    expect(screen.getByText('Mathematics')).toBeInTheDocument();

    // Create
    await userEvent.click(screen.getByRole('button', { name: 'Assign teacher' }));
    await userEvent.click(screen.getByRole('combobox', { name: 'Teacher' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Aisha Teacher (teacher@school.test)' }),
    );
    await userEvent.click(screen.getByRole('combobox', { name: 'Subject' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Mathematics' }));
    await userEvent.click(screen.getByRole('button', { name: 'Assign' }));

    expect(createBodies.length).toBe(1);
    expect(createBodies[0]).toMatchObject({
      teacher_id: 'u1',
      section_id: 's1',
      subject_id: 'sub1',
    });

    // Remove
    await userEvent.click(screen.getAllByRole('button', { name: 'Remove' })[0]);
    expect(deleted).toEqual(['a1']);
  });
});

describe('Enrollments (REQ-FE-AC-06)', () => {
  it('lists, enrolls from roster, and removes enrollments', async () => {
    const enrollments = [
      {
        id: 'e1',
        academic_year_id: 'y1',
        student_id: 'u2',
        section_id: 's1',
        enrolled_at: '2026-01-15T00:00:00Z',
        status: 'active',
      },
    ];
    const createBodies: unknown[] = [];
    const deleted: string[] = [];

    server.use(
      http.get('/api/v1/sections/:id/enrollments', () =>
        HttpResponse.json(enrollments),
      ),
      http.get('/api/v1/users', () =>
        HttpResponse.json([
          makeUser({ id: 'u2', email: 'student@school.test', person: { ...makeUser().person, id: 'p2', name: 'Ben Learner' } }),
          makeUser({ id: 'u3', email: 'student2@school.test', person: { ...makeUser().person, id: 'p3', name: 'Cara Learner' } }),
        ]),
      ),
      http.post('/api/v1/sections/:id/enrollments', async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>;
        createBodies.push({ section_id: params.id, ...body });
        const created = {
          id: 'e2',
          academic_year_id: 'y1',
          student_id: body.student_id as string,
          section_id: params.id as string,
          enrolled_at: '2026-01-16T00:00:00Z',
          status: 'active',
        };
        enrollments.push(created);
        return HttpResponse.json(created, { status: 201 });
      }),
      http.delete('/api/v1/enrollments/:id', ({ params }) => {
        deleted.push(params.id as string);
        return new HttpResponse(null, { status: 204 });
      }),
    );

    renderWithProviders(<Enrollments sectionId="s1" />, { claims: adminClaims });

    expect(await screen.findByText('Ben Learner')).toBeInTheDocument();

    // Enroll from roster
    await userEvent.click(screen.getByRole('button', { name: 'Enroll student' }));
    await userEvent.click(screen.getByRole('combobox', { name: 'Student' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Cara Learner (student2@school.test)' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Enroll' }));

    expect(createBodies.length).toBe(1);
    expect(createBodies[0]).toMatchObject({ student_id: 'u3', section_id: 's1' });

    // Remove
    await userEvent.click(screen.getAllByRole('button', { name: 'Remove' })[0]);
    expect(deleted).toEqual(['e1']);
  });
});
