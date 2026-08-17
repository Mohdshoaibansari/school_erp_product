import { describe, expect, it } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/server';
import { renderWithProviders } from '../../../test/testUtils';
import type { JwtClaims } from '../../../core/auth/session';
import type {
  FeeAssignmentDTO,
  FeeTypeDTO,
  PaymentDTO,
} from '../../../core/api/dto/fees';
import type { UserDTO } from '../../../core/api/dto/users';
import { FeeTypes } from '../FeeTypes';
import { FeeAssignments } from '../FeeAssignments';
import { Payments } from '../Payments';

const adminClaims: JwtClaims & { sub: string } = {
  sub: 'a1',
  roles: ['institution_admin'],
  user_tier: 'institution',
  client_id: 'c1',
  institution_id: 'i1',
};

function makeFeeType(overrides: Partial<FeeTypeDTO> = {}): FeeTypeDTO {
  return {
    id: 'ft1',
    client_id: 'c1',
    institution_id: 'i1',
    name: 'Tuition Fee',
    description: null,
    default_amount: '5000.00',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeFeeAssignment(
  overrides: Partial<FeeAssignmentDTO> = {},
): FeeAssignmentDTO {
  return {
    id: 'fa1',
    client_id: 'c1',
    institution_id: 'i1',
    user_id: 'u1',
    fee_type_id: 'ft1',
    amount: '5000.00',
    due_date: '2026-12-31',
    term_id: null,
    status: 'pending',
    assigned_by: null,
    notes: null,
    created_at: '2026-01-01T00:00:00Z',
    total_paid: '0.00',
    ...overrides,
  };
}

function makePayment(overrides: Partial<PaymentDTO> = {}): PaymentDTO {
  return {
    id: 'p1',
    client_id: 'c1',
    institution_id: 'i1',
    fee_assignment_id: 'fa1',
    amount: '5000.00',
    payment_date: '2026-06-01',
    payment_method: 'cash',
    receipt_number: 'REC-0001',
    reference_number: null,
    recorded_by: null,
    notes: null,
    created_at: '2026-06-01T00:00:00Z',
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

describe('FeeTypes (REQ-FE-FEE-01)', () => {
  it('lists, creates, and deactivates fee types', async () => {
    const feeTypes: FeeTypeDTO[] = [makeFeeType()];
    const createBodies: unknown[] = [];
    const deleted: string[] = [];

    server.use(
      http.get('/api/v1/fee-types', () => HttpResponse.json(feeTypes)),
      http.post('/api/v1/fee-types', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        createBodies.push(body);
        const created = makeFeeType({
          id: 'ft2',
          name: body.name as string,
          default_amount: body.default_amount as string,
        });
        feeTypes.push(created);
        return HttpResponse.json(created, { status: 201 });
      }),
      http.delete('/api/v1/fee-types/:id', ({ params }) => {
        deleted.push(params.id as string);
        return new HttpResponse(null, { status: 204 });
      }),
    );

    renderWithProviders(<FeeTypes />, { claims: adminClaims });

    expect(await screen.findByText('Tuition Fee')).toBeInTheDocument();

    // Create
    await userEvent.click(screen.getByRole('button', { name: 'New fee type' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Name' }), 'Transport Fee');
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Default amount' }),
      '2000',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('Transport Fee')).toBeInTheDocument();
    expect(createBodies.length).toBe(1);
    expect(createBodies[0]).toMatchObject({
      name: 'Transport Fee',
      default_amount: '2000',
      institution_id: 'i1',
    });

    // Deactivate (soft delete) the first fee type
    await userEvent.click(
      screen.getAllByRole('button', { name: 'Deactivate' })[0],
    );
    expect(deleted).toEqual(['ft1']);
  });

  it('edits a fee type', async () => {
    const feeTypes: FeeTypeDTO[] = [makeFeeType()];
    const patchBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/fee-types', () => HttpResponse.json(feeTypes)),
      http.patch('/api/v1/fee-types/:id', async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>;
        patchBodies.push({ id: params.id, ...body });
        return HttpResponse.json(
          makeFeeType({
            id: params.id as string,
            name: body.name as string,
            default_amount: body.default_amount as string,
          }),
        );
      }),
    );

    renderWithProviders(<FeeTypes />, { claims: adminClaims });

    await screen.findByText('Tuition Fee');
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));

    const nameInput = screen.getByRole('textbox', { name: 'Name' });
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Tuition Fee Updated');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(patchBodies.length).toBe(1);
    expect(patchBodies[0]).toMatchObject({ id: 'ft1', name: 'Tuition Fee Updated' });
  });
});

describe('FeeAssignments (REQ-FE-FEE-02, REQ-FE-FEE-04)', () => {
  it('assigns a fee per-student and records a waiver (cohort flag off)', async () => {
    const assignments: FeeAssignmentDTO[] = [makeFeeAssignment()];
    const createBodies: unknown[] = [];
    const waiveBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/fee-assignments', () => HttpResponse.json(assignments)),
      http.get('/api/v1/fee-types', () => HttpResponse.json([makeFeeType()])),
      http.get('/api/v1/users', () => HttpResponse.json([makeUser()])),
      http.get('/api/v1/config/resolve/:keyName', () =>
        HttpResponse.json({
          key: 'fees.cohortBulkAssignment',
          resolved_value: false,
          source_scope: 'platform:default',
        }),
      ),
      http.post('/api/v1/fee-assignments', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        createBodies.push(body);
        const created = makeFeeAssignment({
          id: 'fa2',
          user_id: (body.user_ids as string[])[0],
          amount: body.amount as string,
          due_date: body.due_date as string,
        });
        assignments.push(created);
        return HttpResponse.json([created], { status: 201 });
      }),
      http.post('/api/v1/fee-assignments/:id/waive', async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>;
        waiveBodies.push({ id: params.id, ...body });
        return HttpResponse.json(
          makeFeeAssignment({ id: params.id as string, status: 'waived' }),
        );
      }),
    );

    renderWithProviders(<FeeAssignments />, { claims: adminClaims });

    // List resolves student + fee type names
    expect(await screen.findByText('Ben Learner')).toBeInTheDocument();
    expect(screen.getByText('Tuition Fee')).toBeInTheDocument();

    // Cohort path is feature-flagged off (R6 dependency)
    expect(
      screen.getByText(/Cohort bulk assignment is pending the R6 Fees backend change/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Bulk assign (cohort)' }),
    ).not.toBeInTheDocument();

    // Per-student assignment
    await userEvent.click(screen.getByRole('button', { name: 'Assign fee' }));
    await userEvent.click(screen.getByRole('combobox', { name: 'Fee type' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Tuition Fee' }),
    );
    await userEvent.click(screen.getByRole('combobox', { name: 'Student' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Ben Learner (student@school.test)' }),
    );
    await userEvent.type(screen.getByRole('textbox', { name: 'Amount' }), '1500');
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Due date' }),
      '2026-12-31',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Assign' }));

    expect(createBodies.length).toBe(1);
    expect(createBodies[0]).toMatchObject({
      fee_type_id: 'ft1',
      amount: '1500',
      due_date: '2026-12-31',
      user_ids: ['u1'],
    });

    // Waive
    await userEvent.click(screen.getAllByRole('button', { name: 'Waive' })[0]);
    const waiveDialog = await screen.findByRole('dialog');
    await userEvent.type(
      within(waiveDialog).getByRole('textbox', { name: 'Reason' }),
      'Scholarship',
    );
    await userEvent.click(within(waiveDialog).getByRole('button', { name: 'Waive' }));

    expect(waiveBodies.length).toBe(1);
    expect(waiveBodies[0]).toMatchObject({ id: 'fa1', reason: 'Scholarship' });
  });

  it('flags the cohort bulk path as pending the R6 backend change', async () => {
    server.use(
      http.get('/api/v1/fee-assignments', () => HttpResponse.json([])),
      http.get('/api/v1/fee-types', () => HttpResponse.json([])),
      http.get('/api/v1/users', () => HttpResponse.json([])),
      http.get('/api/v1/config/resolve/:keyName', () =>
        HttpResponse.json({
          key: 'fees.cohortBulkAssignment',
          resolved_value: true,
          source_scope: 'institution:i1',
        }),
      ),
    );

    renderWithProviders(<FeeAssignments />, { claims: adminClaims });

    await screen.findByText(/Cohort bulk assignment is pending/);

    await userEvent.click(
      await screen.findByRole('button', { name: 'Bulk assign (cohort)' }),
    );

    expect(
      await screen.findByText(/Pending R6 Fees backend change/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Cohort-level targets \(section\/grade\) require a Fees backend change/),
    ).toBeInTheDocument();
  });
});

describe('Payments (REQ-FE-FEE-03)', () => {
  it('records a payment and filters the list by student', async () => {
    const payments: PaymentDTO[] = [
      makePayment(),
      makePayment({
        id: 'p2',
        fee_assignment_id: 'fa2',
        receipt_number: 'REC-0002',
        amount: '2000.00',
        payment_date: '2026-06-02',
      }),
    ];
    const recordBodies: unknown[] = [];

    server.use(
      http.get('/api/v1/payments', () => HttpResponse.json(payments)),
      http.get('/api/v1/fee-assignments', () =>
        HttpResponse.json([
          makeFeeAssignment(),
          makeFeeAssignment({
            id: 'fa2',
            user_id: 'u2',
            fee_type_id: 'ft2',
            status: 'partial',
          }),
        ]),
      ),
      http.get('/api/v1/fee-types', () =>
        HttpResponse.json([
          makeFeeType(),
          makeFeeType({ id: 'ft2', name: 'Transport Fee', default_amount: '2000.00' }),
        ]),
      ),
      http.get('/api/v1/users', () =>
        HttpResponse.json([
          makeUser(),
          makeUser({ id: 'u2', email: 'cara@school.test', name: 'Cara Learner' }),
        ]),
      ),
      http.post('/api/v1/payments', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        recordBodies.push(body);
        const created = makePayment({
          id: 'p3',
          fee_assignment_id: body.fee_assignment_id as string,
          amount: body.amount as string,
          payment_method: body.payment_method as string,
          receipt_number: 'REC-0003',
        });
        payments.push(created);
        return HttpResponse.json(created, { status: 201 });
      }),
    );

    renderWithProviders(<Payments />, { claims: adminClaims });

    // List (names resolved from assignments + fee types)
    expect(await screen.findByText('Ben Learner')).toBeInTheDocument();
    expect(screen.getByText('Cara Learner')).toBeInTheDocument();

    // Record a payment
    await userEvent.click(screen.getByRole('button', { name: 'Record payment' }));
    await userEvent.click(screen.getByRole('combobox', { name: 'Fee assignment' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Ben Learner — Tuition Fee' }),
    );
    await userEvent.type(screen.getByRole('textbox', { name: 'Amount' }), '1500');
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Payment method' }),
      'cash',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Record' }));

    expect(recordBodies.length).toBe(1);
    expect(recordBodies[0]).toMatchObject({
      fee_assignment_id: 'fa1',
      amount: '1500',
      payment_method: 'cash',
    });

    // Filter by student
    await userEvent.type(
      screen.getByTestId('payments-filter-student'),
      'Cara',
    );
    expect(screen.getByText('Cara Learner')).toBeInTheDocument();
    expect(screen.queryByText('Ben Learner')).not.toBeInTheDocument();
  });
});
