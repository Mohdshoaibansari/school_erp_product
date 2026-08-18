import { useState } from 'react';
import {
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { platformApi } from '../../core/api/platform';
import { usersApi } from '../../core/api/users';
import { lookupsApi } from '../../core/api/lookups';
import type {
  ClientUserCreateDTO,
  ClientUserDTO,
} from '../../core/api/dto/users';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { TableSkeleton } from '../../components/Skeleton';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';

type ModalState = { kind: 'create' } | { kind: 'transition'; user: ClientUserDTO } | null;

/** Allowed transitions from each user lifecycle state (matches backend state machine). */
const USER_ALLOWED_TRANSITIONS: Record<string, string[]> = {
  invited: ['active'],
  pending: ['active'],
  active: ['suspended', 'archived'],
  suspended: ['active', 'archived'],
  archived: [],
};

export function ClientUsers() {
  const { clientId = '' } = useParams();
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({ email: '', name: '', role_id: '' });
  const [transitionState, setTransitionState] = useState('');

  const clientQuery = useQuery({
    queryKey: ['platform', 'clients', clientId],
    queryFn: () => platformApi.getClient(clientId).then((r) => r.data),
    enabled: !!clientId,
  });

  const usersQuery = useQuery({
    queryKey: ['platform', 'clients', clientId, 'users'],
    queryFn: () => usersApi.listClientUsers(clientId).then((r) => r.data),
    enabled: !!clientId,
  });

  const rolesQuery = useQuery({
    queryKey: ['lookups', 'roles'],
    queryFn: () => lookupsApi.listRoles().then((r) => r.data),
  });

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ['platform', 'clients', clientId, 'users'],
    });

  const createMutation = useMutation({
    mutationFn: (payload: ClientUserCreateDTO) =>
      usersApi.createClientUser(clientId, payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const transitionMutation = useMutation({
    mutationFn: (vars: { userId: string; new_state: string }) =>
      usersApi
        .transitionClientUser(clientId, vars.userId, {
          new_state: vars.new_state,
          reason: null,
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

  const columns: DataTableColumn<ClientUserDTO>[] = [
    { key: 'name', header: 'Name', render: (u) => u.person.name },
    { key: 'email', header: 'Email', render: (u) => u.email },
    {
      key: 'status',
      header: 'Status',
      render: (u) => <StatusPill status={u.lifecycle_status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (u) => (
        <Button size="xs" variant="light" onClick={() => {
          setTransitionState(USER_ALLOWED_TRANSITIONS[u.lifecycle_status]?.[0] ?? '');
          setModal({ kind: 'transition', user: u });
        }}>
          Transition
        </Button>
      ),
    },
  ];

  if (usersQuery.isLoading) {
    return (
      <>
        <PageHeader
          title={clientQuery.data?.display_name ?? 'Client users'}
          subtitle="Manage client-director users for this client."
        />
        <TableSkeleton rows={5} columns={4} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={clientQuery.data?.display_name ?? 'Client users'}
        subtitle="Manage client-director users for this client."
        actions={
          <Button onClick={() => setModal({ kind: 'create' })}>
            Invite user
          </Button>
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <Text size="sm" c="dimmed" mb="md">
        Users are bootstrapped in an invited state; they activate via the invite link.
      </Text>

      <DataTable
        columns={columns}
        rows={usersQuery.data ?? []}
        getRowKey={(u) => u.id}
      />

      <Modal opened={modal?.kind === 'create'} onClose={() => setModal(null)} title="Invite client user">
        <Stack>
          <TextInput
            label="Name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <TextInput
            label="Email"
            required
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.currentTarget.value })}
          />
          <Select
            label="Role"
            required
            searchable
            data={(rolesQuery.data ?? []).map((r) => ({ value: r.id, label: r.name }))}
            value={form.role_id || null}
            onChange={(v) => setForm({ ...form, role_id: v ?? '' })}
          />
          <Button
            loading={createMutation.isPending}
            onClick={() =>
              createMutation.mutate({
                email: form.email,
                person_data: { name: form.name },
                role_id: form.role_id,
                client_id: null,
              })
            }
          >
            Invite
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={modal?.kind === 'transition'}
        onClose={() => setModal(null)}
        title="Transition client user"
      >
        <Stack>
          <Select
            label="New state"
            data={USER_ALLOWED_TRANSITIONS[modal?.kind === 'transition' ? modal.user.lifecycle_status : ''] ?? []}
            value={transitionState}
            onChange={(v) => setTransitionState(v ?? '')}
          />
          <Group justify="flex-end">
            <Button
              loading={transitionMutation.isPending}
              onClick={() => {
                const user = modal?.kind === 'transition' ? modal.user : null;
                if (user && transitionState) {
                  transitionMutation.mutate({
                    userId: user.id,
                    new_state: transitionState,
                  });
                }
              }}
            >
              Transition
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
