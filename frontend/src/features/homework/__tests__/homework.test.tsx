import { describe, expect, it } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/server';
import { renderWithProviders } from '../../../test/testUtils';
import type { JwtClaims } from '../../../core/auth/session';
import type {
  GradeDTO,
  HomeworkDTO,
  SubmissionDTO,
} from '../../../core/api/dto/homework';
import type { UserDTO } from '../../../core/api/dto/users';
import type {
  AcademicStructureDTO,
  AcademicYearDTO,
  SubjectDTO,
} from '../../../core/api/dto/academic';
import Homeworks from '../Homeworks';
import Submissions from '../Submissions';
import Grades from '../Grades';

const adminClaims: JwtClaims & { sub: string } = {
  sub: 'a1',
  roles: ['institution_admin'],
  user_tier: 'institution',
  client_id: 'c1',
  institution_id: 'i1',
};

const cdClaims: JwtClaims & { sub: string } = {
  sub: 'cd1',
  roles: ['client_director'],
  user_tier: 'client_leadership',
  client_id: 'c1',
  institution_id: null,
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
      { id: 'c1', academic_year_id: 'y1', grade_level_id: 'g1', name: '10A', sort_order: 1 },
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

function makeSubject(): SubjectDTO {
  return {
    id: 'sub1',
    academic_year_id: 'y1',
    name: 'Mathematics',
    code: 'MATH101',
    sort_order: 1,
  };
}

function makeHomework(overrides: Partial<HomeworkDTO> = {}): HomeworkDTO {
  return {
    id: 'h1',
    client_id: 'c1',
    institution_id: 'i1',
    title: 'Algebra HW',
    description: null,
    subject_id: 'sub1',
    grade_level_id: null,
    section_id: 's1',
    due_date: '2026-05-30',
    max_score: 100,
    status: 'active',
    assigned_by: null,
    created_at: '2026-01-01T00:00:00Z',
    submission_count: 0,
    ...overrides,
  };
}

function makeSubmission(overrides: Partial<SubmissionDTO> = {}): SubmissionDTO {
  return {
    id: 'sub1',
    client_id: 'c1',
    institution_id: 'i1',
    homework_id: 'h1',
    student_id: 'u1',
    content: 'My essay content',
    status: 'submitted',
    submitted_at: '2026-05-20T00:00:00Z',
    created_at: '2026-05-20T00:00:00Z',
    student_name: 'Ben Learner',
    ...overrides,
  };
}

function makeGrade(overrides: Partial<GradeDTO> = {}): GradeDTO {
  return {
    id: 'g1',
    client_id: 'c1',
    institution_id: 'i1',
    submission_id: 'sub1',
    score: 85,
    max_score: 100,
    feedback: 'Good',
    graded_by: null,
    graded_at: '2026-05-21T00:00:00Z',
    created_at: '2026-05-21T00:00:00Z',
    ...overrides,
  };
}

function makeUser(overrides: Partial<UserDTO> = {}): UserDTO {
  return {
    id: 'u1',
    client_id: 'c1',
    institution_id: 'i1',
    email: 'student@school.test',
    name: 'Ben Learner',
    user_category_id: 'uc1',
    lifecycle_status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('Homeworks (REQ-FE-HW-01, REQ-FE-HW-04)', () => {
  it('lists, creates, and closes homework', async () => {
    const homeworks: HomeworkDTO[] = [makeHomework()];
    const createBodies: unknown[] = [];
    const closeBodies: string[] = [];

    server.use(
      http.get('/api/v1/homeworks', () => HttpResponse.json(homeworks)),
      http.get('/api/v1/subjects', () => HttpResponse.json([makeSubject()])),
      http.get('/api/v1/academic-years', () => HttpResponse.json([makeYear()])),
      http.get('/api/v1/academic-years/:id/structure', () =>
        HttpResponse.json(makeStructure()),
      ),
      http.post('/api/v1/homeworks', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        createBodies.push(body);
        const created = makeHomework({
          id: 'h2',
          title: body.title as string,
          due_date: body.due_date as string,
          subject_id: body.subject_id as string | null,
          section_id: body.section_id as string | null,
          max_score: body.max_score as number | null,
        });
        homeworks.push(created);
        return HttpResponse.json(created, { status: 201 });
      }),
      http.post('/api/v1/homeworks/:id/close', ({ params }) => {
        closeBodies.push(params.id as string);
        return HttpResponse.json(
          makeHomework({ id: params.id as string, status: 'closed' }),
        );
      }),
    );

    renderWithProviders(<Homeworks />, { claims: adminClaims });

    expect(await screen.findByText('Algebra HW')).toBeInTheDocument();

    // Create
    await userEvent.click(screen.getByRole('button', { name: 'New homework' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Title' }), 'Essay HW');
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Instructions' }),
      'Write an essay',
    );
    await userEvent.click(screen.getByRole('combobox', { name: 'Subject' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Mathematics' }),
    );
    await userEvent.click(screen.getByRole('combobox', { name: 'Section' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Grade 10 10A · A' }),
    );
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Due date' }),
      '2026-06-01',
    );
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Max score' }),
      '50',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('Essay HW')).toBeInTheDocument();
    expect(createBodies.length).toBe(1);
    expect(createBodies[0]).toMatchObject({
      title: 'Essay HW',
      subject_id: 'sub1',
      section_id: 's1',
      due_date: '2026-06-01',
      max_score: 50,
    });

    // Close
    await userEvent.click(screen.getAllByRole('button', { name: 'Close' })[0]);
    expect(closeBodies).toEqual(['h1']);
  });

  it('restricts homework authoring to Institution Admin', async () => {
    renderWithProviders(<Homeworks />, { claims: cdClaims });

    // Client Director has no institution context → no authoring actions.
    expect(
      screen.queryByRole('button', { name: 'New homework' }),
    ).not.toBeInTheDocument();
  });
});

describe('Submissions (REQ-FE-HW-02)', () => {
  it('lists, views, and grades a submission', async () => {
    const gradeBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/homeworks/:id', () => HttpResponse.json(makeHomework())),
      http.get('/api/v1/submissions', () =>
        HttpResponse.json([makeSubmission()]),
      ),
      http.post('/api/v1/submissions/:id/grade', async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>;
        gradeBodies.push({ id: params.id, ...body });
        return HttpResponse.json(
          makeGrade({
            submission_id: params.id as string,
            score: body.score as number,
            feedback: body.feedback as string | null,
          }),
          { status: 201 },
        );
      }),
    );

    renderWithProviders(
      <Routes>
        <Route path="/homework/:hwId/submissions" element={<Submissions />} />
      </Routes>,
      { route: '/homework/h1/submissions', claims: adminClaims },
    );

    expect(await screen.findByText('Ben Learner')).toBeInTheDocument();

    // View submitted work
    await userEvent.click(screen.getByRole('button', { name: 'View' }));
    const viewDialog = await screen.findByRole('dialog');
    expect(within(viewDialog).getByText('My essay content')).toBeInTheDocument();
    await userEvent.click(within(viewDialog).getByRole('button', { name: 'Close' }));

    // Grade the submission
    await userEvent.click(screen.getByRole('button', { name: 'Grade' }));
    const gradeDialog = await screen.findByRole('dialog');
    await userEvent.type(
      within(gradeDialog).getByRole('textbox', { name: 'Score' }),
      '90',
    );
    await userEvent.type(
      within(gradeDialog).getByRole('textbox', { name: 'Feedback' }),
      'Great work',
    );
    await userEvent.click(
      within(gradeDialog).getByRole('button', { name: 'Grade' }),
    );

    expect(gradeBodies.length).toBe(1);
    expect(gradeBodies[0]).toMatchObject({
      id: 'sub1',
      score: 90,
      feedback: 'Great work',
    });
  });
});

describe('Grades (REQ-FE-HW-03)', () => {
  it('lists grades per homework and student, and updates a grade', async () => {
    const patchBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/grades', () => HttpResponse.json([makeGrade()])),
      http.get('/api/v1/submissions', () =>
        HttpResponse.json([makeSubmission()]),
      ),
      http.get('/api/v1/homeworks', () => HttpResponse.json([makeHomework()])),
      http.get('/api/v1/users', () => HttpResponse.json([makeUser()])),
      http.patch('/api/v1/grades/:id', async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>;
        patchBodies.push({ id: params.id, ...body });
        return HttpResponse.json(
          makeGrade({
            id: params.id as string,
            score: body.score as number,
            feedback: body.feedback as string | null,
          }),
        );
      }),
    );

    renderWithProviders(<Grades />, { claims: adminClaims });

    expect(await screen.findByText('Ben Learner')).toBeInTheDocument();
    expect(screen.getAllByText('Algebra HW').length).toBeGreaterThan(0);
    expect(screen.getByText('85 / 100')).toBeInTheDocument();

    // Update where the API supports it
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));
    const scoreInput = screen.getByRole('textbox', { name: 'Score' });
    await userEvent.clear(scoreInput);
    await userEvent.type(scoreInput, '92');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(patchBodies.length).toBe(1);
    expect(patchBodies[0]).toMatchObject({ id: 'g1', score: 92 });
  });
});
