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
import { useNavigate } from 'react-router-dom';
import { usersApi } from '../../core/api/users';
import { lookupsApi } from '../../core/api/lookups';
import type { UserCreateDTO, UserDTO } from '../../core/api/dto/users';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';

type ModalState =
  | { kind: 'create' }
  | { kind: 'edit'; user: UserDTO }
  | { kind: 'transition'; user: UserDTO }
  | null;

const LIFECYCLE_STATES = ['active', 'suspended', 'archived'];

export default function Users() {
  const navigate = useNavigate();
  const { institutionId } = useTenant();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({
    email: '',
    name: '',
    user_category_id: '',
    role_id: '',
  });
  const [transitionState, setTransitionState] = useState<string | null>(null);
  const [transitionReason, setTransitionReason] = useState('');

  const usersQuery = useQuery({
    queryKey: ['users', institutionId],
    queryFn: () => usersApi.listUsers().then((r) => r.data),
    enabled: !!institutionId,
  });

  const categoriesQuery = useQuery({
    queryKey: ['lookups', 'user-categories'],
    queryFn: () => lookupsApi.listUserCategories().then((r) => r.data),
  });

  const rolesQuery = useQuery({
    queryKey: ['lookups', 'roles'],
    queryFn: () => lookupsApi.listRoles().then((r) => r.data),
    enabled: modal?.kind === 'create',
  });

  const filtered = useMemo(() => {
    const term = search.toLowerCase();
    return (usersQuery.data ?? []).filter(
      (u) =>
        u.name.toLowerCase().includes(term) || u.email.toLowerCase().includes(term),
    );
  }, [usersQuery.data, search]);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['users', institutionId] });

  const createMutation = useMutation({
    mutationFn: (payload: UserCreateDTO) =>
      usersApi.createUser(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (vars: { id: string; name: string }) =>
      usersApi.updateUser(vars.id, { name: vars.name }).then((r) => r.data),
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
      usersApi
        .transitionUser(vars.id, { new_state: vars.new_state, reason: vars.reason })
        .then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const columns: DataTableColumn<UserDTO>[] = [
    { key: 'name', header: 'Name', render: (u) => u.name },
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
        <Group gap="xs" wrap="nowrap">
          <Button size="xs" variant="light" onClick={() => navigate(`/users/${u.id}`)}>
            Profile
          </Button>
          <Button size="xs" variant="light" onClick={() => {
            setForm({ email: u.email, name: u.name, user_category_id: u.user_category_id, role_id: '' });
            setModal({ kind: 'edit', user: u });
          }}>
            Edit
          </Button>
          <Button size="xs" variant="light" onClick={() => {
            setTransitionState(u.lifecycle_status);
            setTransitionReason('');
            setModal({ kind: 'transition', user: u });
          }}>
            Transition
          </Button>
        </Group>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Users"
        subtitle="Users scoped to your institution."
        actions={
          <Group>
            <TextInput
              placeholder="Search users"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
            />
            <Button onClick={() => {
              setForm({ email: '', name: '', user_category_id: '', role_id: '' });
              setModal({ kind: 'create' });
            }}>
              New user
            </Button>
          </Group>
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <DataTable columns={columns} rows={filtered} getRowKey={(u) => u.id} />

      <Modal opened={modal?.kind === 'create'} onClose={() => setModal(null)} title="New user">
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
            label="User category"
            searchable
            data={(categoriesQuery.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            value={form.user_category_id || null}
            onChange={(v) => setForm({ ...form, user_category_id: v ?? '' })}
          />
          <Select
            label="Role (optional)"
            searchable
            clearable
            data={(rolesQuery.data ?? []).map((r) => ({ value: r.id, label: r.name }))}
            value={form.role_id || null}
            onChange={(v) => setForm({ ...form, role_id: v ?? '' })}
          />
          <Button
            loading={createMutation.isPending}
            disabled={!institutionId}
            onClick={() =>
              createMutation.mutate({
                email: form.email,
                name: form.name,
                user_category_id: form.user_category_id,
                institution_id: institutionId ?? '',
                role_id: form.role_id || null,
              })
            }
          >
            Create
          </Button>
        </Stack>
      </Modal>

      <Modal opened={modal?.kind === 'edit'} onClose={() => setModal(null)} title="Edit user">
        <Stack>
          <TextInput
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <Button
            loading={updateMutation.isPending}
            onClick={() => {
              const user = modal?.kind === 'edit' ? modal.user : null;
              if (user) updateMutation.mutate({ id: user.id, name: form.name });
            }}
          >
            Save
          </Button>
        </Stack>
      </Modal>

      <Modal opened={modal?.kind === 'transition'} onClose={() => setModal(null)} title="Transition user">
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
              const user = modal?.kind === 'transition' ? modal.user : null;
              if (user && transitionState) {
                transitionMutation.mutate({
                  id: user.id,
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
