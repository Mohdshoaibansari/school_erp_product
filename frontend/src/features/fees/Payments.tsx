import { useMemo, useState } from 'react';
import {
  Button,
  Group,
  Modal,
  Select,
  Stack,
  TextInput,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { feesApi } from '../../core/api/fees';
import { usersApi } from '../../core/api/users';
import type { PaymentCreateDTO, PaymentDTO } from '../../core/api/dto/fees';
import type { FeeAssignmentDTO } from '../../core/api/dto/fees';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';
import { usePermissions } from '../../core/access/usePermissions';

interface PaymentRow {
  payment: PaymentDTO;
  studentName: string;
  feeTypeName: string;
  status: string;
}

export default function Payments() {
  const { institutionId } = useTenant();
  const { can } = usePermissions();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({
    fee_assignment_id: '',
    amount: '',
    payment_method: '',
    payment_date: '',
    reference_number: '',
    notes: '',
  });
  const [filters, setFilters] = useState({
    student: '',
    fee: '',
    date: '',
    status: '',
  });

  const paymentsQuery = useQuery({
    queryKey: ['payments', institutionId],
    queryFn: () => feesApi.listPayments().then((r) => r.data),
    enabled: !!institutionId,
  });

  const assignmentsQuery = useQuery({
    queryKey: ['fee-assignments', institutionId],
    queryFn: () => feesApi.listFeeAssignments().then((r) => r.data),
    enabled: !!institutionId,
  });

  const feeTypesQuery = useQuery({
    queryKey: ['fee-types', institutionId],
    queryFn: () => feesApi.listFeeTypes().then((r) => r.data),
    enabled: !!institutionId,
  });

  const usersQuery = useQuery({
    queryKey: ['users', institutionId],
    queryFn: () => usersApi.listUsers().then((r) => r.data),
    enabled: !!institutionId,
  });

  const studentNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const u of usersQuery.data ?? []) {
      map.set(u.id, u.name);
    }
    return map;
  }, [usersQuery.data]);

  const feeTypeNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const t of feeTypesQuery.data ?? []) {
      map.set(t.id, t.name);
    }
    return map;
  }, [feeTypesQuery.data]);

  const assignmentById = useMemo(() => {
    const map = new Map<string, FeeAssignmentDTO>();
    for (const a of assignmentsQuery.data ?? []) {
      map.set(a.id, a);
    }
    return map;
  }, [assignmentsQuery.data]);

  const rows = useMemo<PaymentRow[]>(() => {
    return (paymentsQuery.data ?? []).map((payment) => {
      const assignment = assignmentById.get(payment.fee_assignment_id);
      return {
        payment,
        studentName: assignment ? studentNames.get(assignment.user_id) ?? assignment.user_id : '—',
        feeTypeName: assignment ? feeTypeNames.get(assignment.fee_type_id) ?? assignment.fee_type_id : '—',
        status: assignment?.status ?? 'pending',
      };
    });
  }, [paymentsQuery.data, assignmentById, studentNames, feeTypeNames]);

  const filteredRows = useMemo(() => {
    const student = filters.student.toLowerCase();
    const fee = filters.fee.toLowerCase();
    return rows.filter((row) => {
      if (student && !row.studentName.toLowerCase().includes(student)) return false;
      if (fee && !row.feeTypeName.toLowerCase().includes(fee)) return false;
      if (filters.date && row.payment.payment_date !== filters.date) return false;
      if (filters.status && row.status !== filters.status) return false;
      return true;
    });
  }, [rows, filters]);

  const payableAssignments = useMemo(() => {
    return (assignmentsQuery.data ?? [])
      .filter((a) => a.status === 'pending' || a.status === 'partial')
      .map((a) => ({
        value: a.id,
        label: `${studentNames.get(a.user_id) ?? a.user_id} — ${feeTypeNames.get(a.fee_type_id) ?? a.fee_type_id}`,
      }));
  }, [assignmentsQuery.data, studentNames, feeTypeNames]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['payments', institutionId] });
    queryClient.invalidateQueries({ queryKey: ['fee-assignments', institutionId] });
  };

  const recordMutation = useMutation({
    mutationFn: (payload: PaymentCreateDTO) =>
      feesApi.recordPayment(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setOpen(false);
      resetForm();
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  function resetForm() {
    setForm({
      fee_assignment_id: '',
      amount: '',
      payment_method: '',
      payment_date: '',
      reference_number: '',
      notes: '',
    });
  }

  const columns: DataTableColumn<PaymentRow>[] = [
    {
      key: 'receipt',
      header: 'Receipt',
      render: (r) => r.payment.receipt_number ?? '—',
    },
    {
      key: 'student',
      header: 'Student',
      render: (r) => r.studentName,
    },
    {
      key: 'fee_type',
      header: 'Fee type',
      render: (r) => r.feeTypeName,
      hideBelow: 900,
    },
    { key: 'amount', header: 'Amount', render: (r) => r.payment.amount },
    {
      key: 'payment_date',
      header: 'Date',
      render: (r) => r.payment.payment_date,
      hideBelow: 640,
    },
    {
      key: 'method',
      header: 'Method',
      render: (r) => r.payment.payment_method,
      hideBelow: 640,
    },
    {
      key: 'status',
      header: 'Assignment status',
      render: (r) => <StatusPill status={r.status} />,
    },
  ];

  return (
    <>
      <PageHeader
        title="Payments"
        subtitle="Record and filter fee payments."
        actions={
          can('institution_admin') ? (
            <Button
              onClick={() => {
                resetForm();
                setForbidden(null);
                setOpen(true);
              }}
            >
              Record payment
            </Button>
          ) : null
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <Group mb="md" grow>
        <TextInput
          placeholder="Filter by student"
          value={filters.student}
          onChange={(e) => setFilters({ ...filters, student: e.currentTarget.value })}
          data-testid="payments-filter-student"
        />
        <TextInput
          placeholder="Filter by fee"
          value={filters.fee}
          onChange={(e) => setFilters({ ...filters, fee: e.currentTarget.value })}
          data-testid="payments-filter-fee"
        />
        <TextInput
          placeholder="Filter by date"
          value={filters.date}
          onChange={(e) => setFilters({ ...filters, date: e.currentTarget.value })}
          data-testid="payments-filter-date"
        />
        <Select
          placeholder="Filter by status"
          clearable
          data={[
            { value: 'pending', label: 'Pending' },
            { value: 'partial', label: 'Partial' },
            { value: 'paid', label: 'Paid' },
            { value: 'waived', label: 'Waived' },
          ]}
          value={filters.status || null}
          onChange={(v) => setFilters({ ...filters, status: v ?? '' })}
          data-testid="payments-filter-status"
        />
      </Group>

      <DataTable
        columns={columns}
        rows={filteredRows}
        getRowKey={(r) => r.payment.id}
      />

      <Modal opened={open} onClose={() => setOpen(false)} title="Record payment">
        <Stack>
          <Select
            label="Fee assignment"
            searchable
            required
            data={payableAssignments}
            value={form.fee_assignment_id || null}
            onChange={(v) =>
              setForm({ ...form, fee_assignment_id: v ?? '' })
            }
          />
          <TextInput
            label="Amount"
            required
            inputMode="decimal"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.currentTarget.value })}
          />
          <TextInput
            label="Payment method"
            required
            placeholder="cash / upi / bank"
            value={form.payment_method}
            onChange={(e) =>
              setForm({ ...form, payment_method: e.currentTarget.value })
            }
          />
          <TextInput
            label="Payment date"
            placeholder="YYYY-MM-DD"
            value={form.payment_date}
            onChange={(e) =>
              setForm({ ...form, payment_date: e.currentTarget.value })
            }
          />
          <TextInput
            label="Reference number"
            value={form.reference_number}
            onChange={(e) =>
              setForm({ ...form, reference_number: e.currentTarget.value })
            }
          />
          <TextInput
            label="Notes"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.currentTarget.value })}
          />
          <Button
            loading={recordMutation.isPending}
            disabled={!form.fee_assignment_id || !form.amount || !form.payment_method}
            onClick={() =>
              recordMutation.mutate({
                fee_assignment_id: form.fee_assignment_id,
                amount: form.amount,
                payment_method: form.payment_method,
                payment_date: form.payment_date || null,
                reference_number: form.reference_number || null,
                notes: form.notes || null,
              })
            }
          >
            Record
          </Button>
        </Stack>
      </Modal>
    </>
  );
}
