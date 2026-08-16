import { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { feesApi } from '../../core/api/fees';
import { configApi } from '../../core/api/config';
import { usersApi } from '../../core/api/users';
import type {
  FeeAssignmentCreateDTO,
  FeeAssignmentDTO,
  FeeAssignmentUpdateDTO,
} from '../../core/api/dto/fees';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';
import { usePermissions } from '../../core/access/usePermissions';

const COHORT_FLAG_KEY = 'fees.cohortBulkAssignment';

type ModalState =
  | { kind: 'create' }
  | { kind: 'edit'; assignment: FeeAssignmentDTO }
  | { kind: 'waive'; assignment: FeeAssignmentDTO }
  | { kind: 'bulk' }
  | null;

export default function FeeAssignments() {
  const { institutionId, clientId } = useTenant();
  const { can } = usePermissions();
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({
    fee_type_id: '',
    student_id: '',
    amount: '',
    due_date: '',
    notes: '',
  });
  const [waiveReason, setWaiveReason] = useState('');

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

  const cohortFlagQuery = useQuery({
    queryKey: ['config-resolve', institutionId, COHORT_FLAG_KEY],
    queryFn: () =>
      configApi
        .resolveKey(COHORT_FLAG_KEY, {
          institution_id: institutionId,
          client_id: clientId,
        })
        .then((r) => r.data),
    enabled: !!institutionId,
  });

  const cohortEnabled = cohortFlagQuery.data?.resolved_value === true;

  const feeTypeNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const t of feeTypesQuery.data ?? []) {
      map.set(t.id, t.name);
    }
    return map;
  }, [feeTypesQuery.data]);

  const studentNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const u of usersQuery.data ?? []) {
      map.set(u.id, u.name);
    }
    return map;
  }, [usersQuery.data]);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['fee-assignments', institutionId] });

  const createMutation = useMutation({
    mutationFn: (payload: FeeAssignmentCreateDTO) =>
      feesApi.createFeeAssignments(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
      resetForm();
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (vars: { id: string; payload: FeeAssignmentUpdateDTO }) =>
      feesApi.updateFeeAssignment(vars.id, vars.payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const waiveMutation = useMutation({
    mutationFn: (vars: { id: string; reason: string }) =>
      feesApi
        .waiveFeeAssignment(vars.id, { reason: vars.reason })
        .then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
      setWaiveReason('');
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  function resetForm() {
    setForm({
      fee_type_id: '',
      student_id: '',
      amount: '',
      due_date: '',
      notes: '',
    });
  }

  function openCreate() {
    resetForm();
    setForbidden(null);
    setModal({ kind: 'create' });
  }

  function openEdit(assignment: FeeAssignmentDTO) {
    setForm({
      fee_type_id: assignment.fee_type_id,
      student_id: assignment.user_id,
      amount: assignment.amount,
      due_date: assignment.due_date,
      notes: assignment.notes ?? '',
    });
    setForbidden(null);
    setModal({ kind: 'edit', assignment });
  }

  function openWaive(assignment: FeeAssignmentDTO) {
    setWaiveReason('');
    setForbidden(null);
    setModal({ kind: 'waive', assignment });
  }

  const columns: DataTableColumn<FeeAssignmentDTO>[] = [
    {
      key: 'student',
      header: 'Student',
      render: (a) => studentNames.get(a.user_id) ?? a.user_id,
    },
    {
      key: 'fee_type',
      header: 'Fee type',
      render: (a) => feeTypeNames.get(a.fee_type_id) ?? a.fee_type_id,
    },
    { key: 'amount', header: 'Amount', render: (a) => a.amount },
    { key: 'due_date', header: 'Due date', render: (a) => a.due_date, hideBelow: 640 },
    {
      key: 'status',
      header: 'Status',
      render: (a) => <StatusPill status={a.status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (a) => (
        <Group gap="xs" wrap="nowrap">
          <Button size="xs" variant="light" onClick={() => openEdit(a)}>
            Edit
          </Button>
          {a.status !== 'waived' ? (
            <Button size="xs" variant="light" onClick={() => openWaive(a)}>
              Waive
            </Button>
          ) : null}
        </Group>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Fee assignments"
        subtitle="Assign fees to students and record waivers."
        actions={
          can('institution_admin') ? (
            <Group>
              {cohortEnabled ? (
                <Button variant="default" onClick={() => setModal({ kind: 'bulk' })}>
                  Bulk assign (cohort)
                </Button>
              ) : null}
              <Button onClick={openCreate}>Assign fee</Button>
            </Group>
          ) : null
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <Alert color="blue" variant="light" mb="md">
        <Text size="sm">
          Cohort bulk assignment is pending the R6 Fees backend change. Per-student
          assignment is available now.
        </Text>
      </Alert>

      <DataTable
        columns={columns}
        rows={assignmentsQuery.data ?? []}
        getRowKey={(a) => a.id}
      />

      <Modal
        opened={modal?.kind === 'create'}
        onClose={() => setModal(null)}
        title="Assign fee"
      >
        <Stack>
          <Select
            label="Fee type"
            searchable
            required
            data={(feeTypesQuery.data ?? []).map((t) => ({
              value: t.id,
              label: t.name,
            }))}
            value={form.fee_type_id || null}
            onChange={(v) => setForm({ ...form, fee_type_id: v ?? '' })}
          />
          <Select
            label="Student"
            searchable
            required
            data={(usersQuery.data ?? []).map((u) => ({
              value: u.id,
              label: `${u.name} (${u.email})`,
            }))}
            value={form.student_id || null}
            onChange={(v) => setForm({ ...form, student_id: v ?? '' })}
          />
          <TextInput
            label="Amount"
            required
            inputMode="decimal"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.currentTarget.value })}
          />
          <TextInput
            label="Due date"
            required
            placeholder="YYYY-MM-DD"
            value={form.due_date}
            onChange={(e) => setForm({ ...form, due_date: e.currentTarget.value })}
          />
          <TextInput
            label="Notes"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.currentTarget.value })}
          />
          <Button
            loading={createMutation.isPending}
            disabled={!form.fee_type_id || !form.student_id || !form.amount || !form.due_date}
            onClick={() =>
              createMutation.mutate({
                fee_type_id: form.fee_type_id,
                amount: form.amount,
                due_date: form.due_date,
                term_id: null,
                user_ids: [form.student_id],
                institution_id: institutionId,
                notes: form.notes || null,
              })
            }
          >
            Assign
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={modal?.kind === 'edit'}
        onClose={() => setModal(null)}
        title="Edit fee assignment"
      >
        <Stack>
          <TextInput
            label="Amount"
            required
            inputMode="decimal"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.currentTarget.value })}
          />
          <TextInput
            label="Due date"
            required
            placeholder="YYYY-MM-DD"
            value={form.due_date}
            onChange={(e) => setForm({ ...form, due_date: e.currentTarget.value })}
          />
          <TextInput
            label="Notes"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.currentTarget.value })}
          />
          <Button
            loading={updateMutation.isPending}
            disabled={!form.amount || !form.due_date}
            onClick={() => {
              const assignment = modal?.kind === 'edit' ? modal.assignment : null;
              if (assignment) {
                updateMutation.mutate({
                  id: assignment.id,
                  payload: {
                    amount: form.amount,
                    due_date: form.due_date,
                    notes: form.notes || null,
                  },
                });
              }
            }}
          >
            Save
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={modal?.kind === 'waive'}
        onClose={() => setModal(null)}
        title="Waive fee"
      >
        <Stack>
          <Text size="sm" c="dimmed">
            Waiving marks this assignment as waived (terminal). This action
            requires a reason.
          </Text>
          <TextInput
            label="Reason"
            required
            value={waiveReason}
            onChange={(e) => setWaiveReason(e.currentTarget.value)}
          />
          <Button
            loading={waiveMutation.isPending}
            disabled={!waiveReason}
            onClick={() => {
              const assignment = modal?.kind === 'waive' ? modal.assignment : null;
              if (assignment) {
                waiveMutation.mutate({ id: assignment.id, reason: waiveReason });
              }
            }}
          >
            Waive
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={modal?.kind === 'bulk'}
        onClose={() => setModal(null)}
        title="Cohort bulk assignment"
      >
        <Stack>
          <Alert color="warning" title="Pending R6 Fees backend change">
            <Text size="sm">
              Cohort-level targets (section/grade) require a Fees backend change
              that is not yet available. Only per-student assignment is supported
              in this build.
            </Text>
          </Alert>
          <Button variant="default" onClick={() => setModal(null)}>
            Close
          </Button>
        </Stack>
      </Modal>
    </>
  );
}
