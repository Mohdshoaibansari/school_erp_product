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
        title={userQuery.data?.person?.name ?? 'User'}
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
          <ProfileTab person={userQuery.data?.person} />
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
  person,
}: {
  person: import('../../core/api/dto/users').PersonDTO | undefined;
}) {
  return (
    <FormCard title="Profile">
      <Stack maw={420}>
        <TextInput
          label="Gender"
          value={person?.gender ?? ''}
          readOnly
        />
        <TextInput
          label="Date of birth"
          value={person?.date_of_birth ?? ''}
          readOnly
        />
        <TextInput
          label="Blood group"
          value={person?.blood_group ?? ''}
          readOnly
        />
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

  const roleMap = new Map((catalogQuery.data ?? []).map((r) => [r.id, r.name]));

  const columns: DataTableColumn<RoleAssignmentDTO>[] = [
    { key: 'role_id', header: 'Role', render: (a) => roleMap.get(a.role_id) ?? a.role_id },
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
            onChange={(value) => setSelectedRoleId(value ?? '')}
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
