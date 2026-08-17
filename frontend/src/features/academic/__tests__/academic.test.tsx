import { describe, expect, it } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/server';
import { renderWithProviders } from '../../../test/testUtils';
import type { JwtClaims } from '../../../core/auth/session';
import type {
  AcademicStructureDTO,
  AcademicYearDTO,
} from '../../../core/api/dto/academic';
import { AcademicYears } from '../AcademicYears';
import { StructureView } from '../StructureView';
import { Subjects } from '../Subjects';
import { SubjectGroups } from '../SubjectGroups';

const adminClaims: JwtClaims & { sub: string } = {
  sub: 'a1',
  roles: ['institution_admin'],
  user_tier: 'institution',
  client_id: 'c1',
  institution_id: 'i1',
};

function makeYear(overrides: Partial<AcademicYearDTO> = {}): AcademicYearDTO {
  return {
    id: 'y1',
    client_id: 'c1',
    institution_id: 'i1',
    name: '2025-26',
    start_date: '2025-06-01',
    end_date: '2026-05-31',
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeStructure(): AcademicStructureDTO {
  return {
    academic_year: makeYear(),
    terms: [],
    grade_levels: [
      { id: 'g1', academic_year_id: 'y1', name: 'Grade 10', sort_order: 1 },
    ],
    classes: [
      {
        id: 'c1',
        academic_year_id: 'y1',
        grade_level_id: 'g1',
        name: '10A',
        sort_order: 1,
      },
    ],
    sections: [
      {
        id: 's1',
        academic_year_id: 'y1',
        class_id: 'c1',
        name: 'A',
        homeroom_teacher_id: null,
        sort_order: 1,
      },
    ],
    subjects: [],
  };
}

describe('AcademicYears (REQ-FE-AC-01, REQ-FE-AC-03)', () => {
  it('lists years and creates a year from the default template', async () => {
    const years: AcademicYearDTO[] = [makeYear()];
    const createBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/academic-years', () => HttpResponse.json(years)),
      http.post('/api/v1/academic-years', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        createBodies.push(body);
        const created = makeYear({
          id: 'y2',
          name: body.name as string,
          status: 'planning',
        });
        years.push(created);
        return HttpResponse.json(created, { status: 201 });
      }),
    );

    renderWithProviders(<AcademicYears />, { claims: adminClaims });

    expect(await screen.findByText('2025-26')).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole('button', { name: 'New academic year' }),
    );
    await userEvent.type(screen.getByRole('textbox', { name: 'Name' }), '2026-27');
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Start date' }),
      '2026-06-01',
    );
    await userEvent.type(
      screen.getByRole('textbox', { name: 'End date' }),
      '2027-05-31',
    );

    // Structure preview for the template path
    expect(
      screen.getByText(/generated from the default template/),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('2026-27')).toBeInTheDocument();
    expect(createBodies.length).toBe(1);
    expect(createBodies[0]).toMatchObject({ name: '2026-27', clone_from: null });
    expect(screen.getByText('Planning')).toBeInTheDocument();
  });

  it('transitions a planning year to active', async () => {
    const years: AcademicYearDTO[] = [makeYear({ status: 'planning' })];
    const transitionBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/academic-years', () => HttpResponse.json(years)),
      http.post(
        '/api/v1/academic-years/:id/transition',
        async ({ request, params }) => {
          const body = (await request.json()) as Record<string, unknown>;
          transitionBodies.push({ id: params.id, ...body });
          return HttpResponse.json(
            makeYear({ id: params.id as string, status: body.new_state as string }),
          );
        },
      ),
    );

    renderWithProviders(<AcademicYears />, { claims: adminClaims });

    await screen.findByText('2025-26');
    await userEvent.click(screen.getByRole('button', { name: 'Transition' }));

    const dialog = await screen.findByRole('dialog');
    await userEvent.click(
      within(dialog).getByRole('combobox', { name: 'New state' }),
    );
    await userEvent.click(await screen.findByRole('option', { name: 'active' }));
    await userEvent.click(
      within(dialog).getByRole('button', { name: 'Transition' }),
    );

    expect(transitionBodies.length).toBe(1);
    expect(transitionBodies[0]).toMatchObject({ id: 'y1', new_state: 'active' });
  });
});

describe('StructureView (REQ-FE-AC-02, REQ-FE-AC-07)', () => {
  function renderStructure() {
    return renderWithProviders(
      <Routes>
        <Route
          path="/academic/years/:yearId/structure"
          element={<StructureView />}
        />
      </Routes>,
      { route: '/academic/years/y1/structure', claims: adminClaims },
    );
  }

  it('navigates the grade level → class → section hierarchy', async () => {
    server.use(
      http.get('/api/v1/academic-years/:id/structure', () =>
        HttpResponse.json(makeStructure()),
      ),
    );

    renderStructure();

    expect(await screen.findByText('Grade 10')).toBeInTheDocument();
    expect(screen.getByText('10A')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'A' })).toBeInTheDocument();
  });

  it('exposes no direct CRUD controls for structure nodes', async () => {
    server.use(
      http.get('/api/v1/academic-years/:id/structure', () =>
        HttpResponse.json(makeStructure()),
      ),
    );

    renderStructure();
    await screen.findByText('Grade 10');

    expect(
      screen.queryByRole('button', {
        name: /new section|add grade|create term|add class|edit section|edit grade|edit term/i,
      }),
    ).not.toBeInTheDocument();
  });
});

describe('Subjects and SubjectGroups (REQ-FE-AC-04, REQ-FE-AC-07)', () => {
  it('lists subjects read-only', async () => {
    server.use(
      http.get('/api/v1/academic-years', () => HttpResponse.json([makeYear()])),
      http.get('/api/v1/subjects', () =>
        HttpResponse.json([
          {
            id: 'sub1',
            academic_year_id: 'y1',
            name: 'Mathematics',
            code: 'MATH101',
            sort_order: 1,
          },
        ]),
      ),
    );

    renderWithProviders(<Subjects />, { claims: adminClaims });

    expect(await screen.findByText('Mathematics')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /create|new|add/i }),
    ).not.toBeInTheDocument();
  });

  it('lists subject groups read-only', async () => {
    server.use(
      http.get('/api/v1/subject-groups', () =>
        HttpResponse.json([{ id: 'sg1', name: 'Science Group' }]),
      ),
    );

    renderWithProviders(<SubjectGroups />, { claims: adminClaims });

    expect(await screen.findByText('Science Group')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /create|new|add/i }),
    ).not.toBeInTheDocument();
  });
});
