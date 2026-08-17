import { useState } from 'react';
import {
  Button,
  Group,
  Modal,
  Select,
  Stack,
  TextInput,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { institutionsApi } from '../../core/api/institutions';
import { lookupsApi } from '../../core/api/lookups';
import type {
  InstitutionCreateDTO,
  InstitutionDTO,
} from '../../core/api/dto/institutions';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';

type ModalState =
  | { kind: 'create' }
  | { kind: 'edit'; institution: InstitutionDTO }
  | { kind: 'transition'; institution: InstitutionDTO }
  | null;

const LIFECYCLE_STATES = ['onboarding', 'active', 'suspended', 'archived'];

export function Institutions() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({
    institution_type_id: '',
    display_name: '',
    legal_name: '',
    code: '',
  });
  const [transitionState, setTransitionState] = useState<string | null>(null);
  const [transitionReason, setTransitionReason] = useState('');

  const institutionsQuery = useQuery({
    queryKey: ['institutions', 'mine'],
    queryFn: () => institutionsApi.listInstitutions(true).then((r) => r.data),
  });

  const typesQuery = useQuery({
    queryKey: ['lookups', 'institution-types'],
    queryFn: () => lookupsApi.listInstitutionTypes().then((r) => r.data),
    enabled: modal?.kind === 'create',
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['institutions', 'mine'] });

  const createMutation = useMutation({
    mutationFn: (payload: InstitutionCreateDTO) =>
      institutionsApi.createInstitution(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (vars: { id: string; payload: Partial<InstitutionCreateDTO> }) =>
      institutionsApi
        .updateInstitution(vars.id, {
          display_name: vars.payload.display_name,
          legal_name: vars.payload.legal_name,
          code: vars.payload.code,
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

  const transitionMutation = useMutation({
    mutationFn: (vars: { id: string; new_state: string; reason: string | null }) =>
      institutionsApi
        .transitionInstitution(vars.id, {
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

  const goLiveMutation = useMutation({
    mutationFn: (id: string) =>
      institutionsApi
        .goLiveInstitution(id, { new_state: 'active', reason: null })
        .then((r) => r.data),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const columns: DataTableColumn<InstitutionDTO>[] = [
    { key: 'display_name', header: 'Institution', render: (i) => i.display_name },
    { key: 'code', header: 'Code', render: (i) => i.code ?? '—', hideBelow: 640 },
    {
      key: 'status',
      header: 'Status',
      render: (i) => <StatusPill status={i.current_lifecycle_status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (i) => (
        <Group gap="xs" wrap="nowrap">
          <Button
            size="xs"
            variant="light"
            onClick={() => navigate(`/institutions/${i.id}/org-units`)}
          >
            Org units
          </Button>
          <Button size="xs" variant="light" onClick={() => {
            setForm({
              institution_type_id: i.institution_type_id,
              display_name: i.display_name,
              legal_name: i.legal_name ?? '',
              code: i.code ?? '',
            });
            setModal({ kind: 'edit', institution: i });
          }}>
            Edit
          </Button>
          <Button size="xs" variant="light" onClick={() => {
            setTransitionState(i.current_lifecycle_status);
            setTransitionReason('');
            setModal({ kind: 'transition', institution: i });
          }}>
            Transition
          </Button>
          {i.current_lifecycle_status === 'onboarding' ? (
            <Button size="xs" color="success" onClick={() => goLiveMutation.mutate(i.id)}>
              Go live
            </Button>
          ) : null}
        </Group>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Institutions"
        subtitle="Institutions under your client."
        actions={
          <Button onClick={() => {
            setForm({ institution_type_id: '', display_name: '', legal_name: '', code: '' });
            setModal({ kind: 'create' });
          }}>
            New institution
          </Button>
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <DataTable
        columns={columns}
        rows={institutionsQuery.data ?? []}
        getRowKey={(i) => i.id}
      />

      <Modal opened={modal?.kind === 'create'} onClose={() => setModal(null)} title="New institution">
        <Stack>
          <TextInput
            label="Display name"
            required
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.currentTarget.value })}
          />
          <Select
            label="Institution type"
            searchable
            data={(typesQuery.data ?? []).map((t) => ({
              value: t.id,
              label: t.code ?? t.id,
            }))}
            value={form.institution_type_id || null}
            onChange={(v) => setForm({ ...form, institution_type_id: v ?? '' })}
          />
          <TextInput
            label="Legal name"
            value={form.legal_name}
            onChange={(e) => setForm({ ...form, legal_name: e.currentTarget.value })}
          />
          <TextInput
            label="Code"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.currentTarget.value })}
          />
          <Button
            loading={createMutation.isPending}
            onClick={() =>
              createMutation.mutate({
                institution_type_id: form.institution_type_id,
                display_name: form.display_name,
                legal_name: form.legal_name || null,
                code: form.code || null,
                primary_contact_email: null,
                primary_contact_phone: null,
                established_year: null,
                affiliation_number: null,
                affiliation_board: null,
              })
            }
          >
            Create
          </Button>
        </Stack>
      </Modal>

      <Modal opened={modal?.kind === 'edit'} onClose={() => setModal(null)} title="Edit institution">
        <Stack>
          <TextInput
            label="Display name"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.currentTarget.value })}
          />
          <TextInput
            label="Legal name"
            value={form.legal_name}
            onChange={(e) => setForm({ ...form, legal_name: e.currentTarget.value })}
          />
          <TextInput
            label="Code"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.currentTarget.value })}
          />
          <Button
            loading={updateMutation.isPending}
            onClick={() => {
              const institution = modal?.kind === 'edit' ? modal.institution : null;
              if (institution) {
                updateMutation.mutate({
                  id: institution.id,
                  payload: form,
                });
              }
            }}
          >
            Save
          </Button>
        </Stack>
      </Modal>

      <Modal opened={modal?.kind === 'transition'} onClose={() => setModal(null)} title="Transition institution">
        <Stack>
          <Select
            label="New state"
            data={LIFECYCLE_STATES}
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
              const institution = modal?.kind === 'transition' ? modal.institution : null;
              if (institution && transitionState) {
                transitionMutation.mutate({
                  id: institution.id,
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
