import { useState } from 'react';
import {
  Button,
  Group,
  Select,
  Stack,
  Tabs,
  TextInput,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { usersApi } from '../../core/api/users';
import { lookupsApi } from '../../core/api/lookups';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { FormCard } from '../../components/FormCard';
import { PermissionDenied } from '../../components/PermissionDenied';
import type {
  UserIdentifierDTO,
  RoleAssignmentDTO,
} from '../../core/api/dto/users';

export function UserDetail() {
  const { userId = '' } = useParams();
  const [forbidden, setForbidden] = useState<string | null>(null);

  const userQuery = useQuery({
    queryKey: ['users', userId],
    queryFn: () => usersApi.getUser(userId).then((r) => r.data),
    enabled: !!userId,
  });

  return (
    <>
      <PageHeader
        title={userQuery.data?.name ?? 'User'}
        subtitle={userQuery.data?.email}
      />
      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}
      <Tabs defaultValue="profile">
        <Tabs.List mb="md">
          <Tabs.Tab value="profile">Profile</Tabs.Tab>
          <Tabs.Tab value="identifiers">Identifiers</Tabs.Tab>
          <Tabs.Tab value="roles">Roles</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="profile">
          <ProfileTab userId={userId} onForbidden={setForbidden} />
        </Tabs.Panel>
        <Tabs.Panel value="identifiers">
          <IdentifiersTab userId={userId} onForbidden={setForbidden} />
        </Tabs.Panel>
        <Tabs.Panel value="roles">
          <RolesTab userId={userId} onForbidden={setForbidden} />
        </Tabs.Panel>
      </Tabs>
    </>
  );
}

function ProfileTab({
  userId,
  onForbidden,
}: {
  userId: string;
  onForbidden: (m: string | null) => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ gender: '', date_of_birth: '', blood_group: '' });

  const profileQuery = useQuery({
    queryKey: ['users', userId, 'profile'],
    queryFn: () => usersApi.getProfile(userId).then((r) => r.data),
    enabled: !!userId,
    retry: false,
  });

  const hasProfile = !!profileQuery.data;

  const saveMutation = useMutation({
    mutationFn: () =>
      usersApi
        .updateProfile(userId, {
          gender: form.gender || null,
          date_of_birth: form.date_of_birth || null,
          blood_group: form.blood_group || null,
        })
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', userId, 'profile'] });
    },
    onError: (err) => {
      if (isForbidden(err)) onForbidden(normalizeApiError(err).message);
    },
  });

  if (profileQuery.isLoading) return null;

  return (
    <FormCard title={hasProfile ? 'Edit profile' : 'Profile'}>
      <Stack maw={420}>
        <TextInput
          label="Gender"
          value={form.gender || profileQuery.data?.gender || ''}
          onChange={(e) => setForm({ ...form, gender: e.currentTarget.value })}
        />
        <TextInput
          label="Date of birth"
          placeholder="YYYY-MM-DD"
          value={form.date_of_birth || profileQuery.data?.date_of_birth || ''}
          onChange={(e) => setForm({ ...form, date_of_birth: e.currentTarget.value })}
        />
        <TextInput
          label="Blood group"
          value={form.blood_group || profileQuery.data?.blood_group || ''}
          onChange={(e) => setForm({ ...form, blood_group: e.currentTarget.value })}
        />
        <Button loading={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
          Save profile
        </Button>
      </Stack>
    </FormCard>
  );
}

function IdentifiersTab({
  userId,
  onForbidden,
}: {
  userId: string;
  onForbidden: (m: string | null) => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ type: '', value: '' });

  const identifiersQuery = useQuery({
    queryKey: ['users', userId, 'identifiers'],
    queryFn: () => usersApi.listIdentifiers(userId).then((r) => r.data),
    enabled: !!userId,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['users', userId, 'identifiers'] });

  const createMutation = useMutation({
    mutationFn: () =>
      usersApi.createIdentifier(userId, form).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setForm({ type: '', value: '' });
    },
    onError: (err) => {
      if (isForbidden(err)) onForbidden(normalizeApiError(err).message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => usersApi.deleteIdentifier(userId, id),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) onForbidden(normalizeApiError(err).message);
    },
  });

  const columns: DataTableColumn<UserIdentifierDTO>[] = [
    { key: 'type', header: 'Type', render: (i) => i.type },
    { key: 'value', header: 'Value', render: (i) => i.value },
    {
      key: 'actions',
      header: 'Actions',
      render: (i) => (
        <Button size="xs" color="danger" onClick={() => deleteMutation.mutate(i.id)}>
          Remove
        </Button>
      ),
    },
  ];

  return (
    <Stack>
      <FormCard title="Add identifier">
        <Group align="end">
          <TextInput
            label="Type"
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.currentTarget.value })}
          />
          <TextInput
            label="Value"
            value={form.value}
            onChange={(e) => setForm({ ...form, value: e.currentTarget.value })}
          />
          <Button loading={createMutation.isPending} onClick={() => createMutation.mutate()}>
            Add
          </Button>
        </Group>
      </FormCard>
      <DataTable
        columns={columns}
        rows={identifiersQuery.data ?? []}
        getRowKey={(i) => i.id}
      />
    </Stack>
  );
}

function RolesTab({
  userId,
  onForbidden,
}: {
  userId: string;
  onForbidden: (m: string | null) => void;
}) {
  const queryClient = useQueryClient();
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);

  const assignmentsQuery = useQuery({
    queryKey: ['users', userId, 'roles'],
    queryFn: () => usersApi.listRoleAssignments(userId).then((r) => r.data),
    enabled: !!userId,
  });

  const catalogQuery = useQuery({
    queryKey: ['lookups', 'roles'],
    queryFn: () => lookupsApi.listRoles().then((r) => r.data),
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['users', userId, 'roles'] });

  const assignMutation = useMutation({
    mutationFn: (roleId: string) =>
      usersApi.createRoleAssignment(userId, { role_id: roleId, scope: null }).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setSelectedRoleId(null);
    },
    onError: (err) => {
      if (isForbidden(err)) onForbidden(normalizeApiError(err).message);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (assignmentId: string) => usersApi.deleteRoleAssignment(userId, assignmentId),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) onForbidden(normalizeApiError(err).message);
    },
  });

  const columns: DataTableColumn<RoleAssignmentDTO>[] = [
    { key: 'role_id', header: 'Role', render: (a) => a.role_id },
    { key: 'scope', header: 'Scope', render: (a) => a.scope ?? '—' },
    {
      key: 'actions',
      header: 'Actions',
      render: (a) => (
        <Button size="xs" color="danger" onClick={() => removeMutation.mutate(a.id)}>
          Remove
        </Button>
      ),
    },
  ];

  return (
    <Stack>
      <FormCard title="Assign role">
        <Group align="end">
          <Select
            label="Role"
            searchable
            data={(catalogQuery.data ?? []).map((r) => ({ value: r.id, label: r.name }))}
            value={selectedRoleId}
            onChange={setSelectedRoleId}
            w={260}
          />
          <Button
            loading={assignMutation.isPending}
            disabled={!selectedRoleId}
            onClick={() => selectedRoleId && assignMutation.mutate(selectedRoleId)}
          >
            Assign
          </Button>
        </Group>
      </FormCard>
      <DataTable
        columns={columns}
        rows={assignmentsQuery.data ?? []}
        getRowKey={(a) => a.id}
      />
    </Stack>
  );
}
