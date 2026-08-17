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
import { useNavigate } from 'react-router-dom';
import { academicApi } from '../../core/api/academic';
import type {
  AcademicYearCreateDTO,
  AcademicYearDTO,
} from '../../core/api/dto/academic';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { TableSkeleton } from '../../components/Skeleton';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';

type ModalState =
  | { kind: 'create' }
  | { kind: 'transition'; year: AcademicYearDTO }
  | null;

const NEXT_STATES: Record<string, string[]> = {
  planning: ['active'],
  active: ['closed'],
  closed: [],
};

export function AcademicYears() {
  const navigate = useNavigate();
  const { institutionId } = useTenant();
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    start_date: '',
    end_date: '',
    clone_from: '',
  });
  const [transitionState, setTransitionState] = useState<string | null>(null);
  const [transitionReason, setTransitionReason] = useState('');

  const yearsQuery = useQuery({
    queryKey: ['academic-years', institutionId],
    queryFn: () => academicApi.listAcademicYears().then((r) => r.data),
    enabled: !!institutionId,
  });

  const cloneOptions = useMemo(
    () => [
      { value: '', label: 'Default template (generate structure)' },
      ...(yearsQuery.data ?? []).map((y) => ({
        value: y.id,
        label: `Clone from ${y.name}`,
      })),
    ],
    [yearsQuery.data],
  );

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ['academic-years', institutionId],
    });

  const createMutation = useMutation({
    mutationFn: (payload: AcademicYearCreateDTO) =>
      academicApi.createAcademicYear(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
      resetForm();
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const transitionMutation = useMutation({
    mutationFn: (vars: { id: string; new_state: string; reason: string | null }) =>
      academicApi
        .transitionAcademicYear(vars.id, {
          new_state: vars.new_state,
          reason: vars.reason,
        })
        .then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  function resetForm() {
    setForm({ name: '', start_date: '', end_date: '', clone_from: '' });
  }

  const columns: DataTableColumn<AcademicYearDTO>[] = [
    { key: 'name', header: 'Name', render: (y) => y.name },
    {
      key: 'period',
      header: 'Period',
      render: (y) => `${y.start_date} → ${y.end_date}`,
      hideBelow: 900,
    },
    {
      key: 'status',
      header: 'Status',
      render: (y) => <StatusPill status={y.status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (y) => (
        <Group gap="xs" wrap="nowrap">
          <Button
            size="xs"
            variant="light"
            onClick={() => navigate(`/academic/years/${y.id}/structure`)}
          >
            View structure
          </Button>
          {(NEXT_STATES[y.status] ?? []).length > 0 ? (
            <Button
              size="xs"
              variant="light"
              onClick={() => {
                setTransitionState(null);
                setTransitionReason('');
                setForbidden(null);
                setModal({ kind: 'transition', year: y });
              }}
            >
              Transition
            </Button>
          ) : null}
        </Group>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Academic years"
        subtitle="Academic years and their lifecycle (planning → active → closed)."
        actions={
          <Button
            onClick={() => {
              resetForm();
              setForbidden(null);
              setModal({ kind: 'create' });
            }}
          >
            New academic year
          </Button>
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      {yearsQuery.isLoading ? <TableSkeleton rows={5} columns={4} /> : null}

      <DataTable
        columns={columns}
        rows={yearsQuery.data ?? []}
        getRowKey={(y) => y.id}
      />

      <Modal
        opened={modal?.kind === 'create'}
        onClose={() => setModal(null)}
        title="New academic year"
      >
        <Stack>
          <TextInput
            label="Name"
            required
            placeholder="2026-27"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <TextInput
            label="Start date"
            required
            placeholder="YYYY-MM-DD"
            value={form.start_date}
            onChange={(e) =>
              setForm({ ...form, start_date: e.currentTarget.value })
            }
          />
          <TextInput
            label="End date"
            required
            placeholder="YYYY-MM-DD"
            value={form.end_date}
            onChange={(e) => setForm({ ...form, end_date: e.currentTarget.value })}
          />
          <Select
            label="Structure source"
            data={cloneOptions}
            value={form.clone_from}
            onChange={(v) => setForm({ ...form, clone_from: v ?? '' })}
          />
          <Alert color="blue" variant="light">
            {form.clone_from
              ? 'Structure will be cloned from the selected year.'
              : 'Structure will be generated from the default template (terms, grade levels, classes, sections).'}
          </Alert>
          <Button
            loading={createMutation.isPending}
            onClick={() =>
              createMutation.mutate({
                name: form.name,
                start_date: form.start_date,
                end_date: form.end_date,
                clone_from: form.clone_from || null,
              })
            }
          >
            Create
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={modal?.kind === 'transition'}
        onClose={() => setModal(null)}
        title="Transition academic year"
      >
        <Stack>
          <Text size="sm" c="dimmed">
            {modal?.kind === 'transition'
              ? `Current status: ${modal.year.status}`
              : ''}
          </Text>
          <Select
            label="New state"
            data={modal?.kind === 'transition' ? NEXT_STATES[modal.year.status] ?? [] : []}
            value={transitionState}
            onChange={setTransitionState}
          />
          <TextInput
            label="Reason"
            value={transitionReason}
            onChange={(e) => setTransitionReason(e.currentTarget.value)}
          />
          <Button
            loading={transitionMutation.isPending}
            onClick={() => {
              const year = modal?.kind === 'transition' ? modal.year : null;
              if (year && transitionState) {
                transitionMutation.mutate({
                  id: year.id,
                  new_state: transitionState,
                  reason: transitionReason || null,
                });
              }
            }}
          >
            Transition
          </Button>
        </Stack>
      </Modal>
    </>
  );
}
