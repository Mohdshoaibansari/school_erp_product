import { useState } from 'react';
import { Button, Modal, Stack, Switch, Text, TextInput } from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { platformApi } from '../../core/api/platform';
import type {
  InstitutionTypeCreateDTO,
  InstitutionTypeDTO,
} from '../../core/api/dto/platform';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { PermissionDenied } from '../../components/PermissionDenied';

type ModalState =
  | { kind: 'create' }
  | { kind: 'edit'; type: InstitutionTypeDTO }
  | null;

export default function InstitutionTypes() {
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({ name_id: '', code: '', is_system: false });

  const typesQuery = useQuery({
    queryKey: ['platform', 'institution-types'],
    queryFn: () => platformApi.listInstitutionTypes().then((r) => r.data),
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['platform', 'institution-types'] });

  const createMutation = useMutation({
    mutationFn: (payload: InstitutionTypeCreateDTO) =>
      platformApi.createInstitutionType(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const editMutation = useMutation({
    mutationFn: (vars: { id: string; template: unknown }) =>
      platformApi
        .updateInstitutionType(vars.id, {
          default_org_unit_template: vars.template,
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

  const columns: DataTableColumn<InstitutionTypeDTO>[] = [
    { key: 'code', header: 'Code', render: (t) => t.code },
    {
      key: 'name_id',
      header: 'Name ID',
      render: (t) => t.name_id,
      hideBelow: 640,
    },
    {
      key: 'is_system',
      header: 'System',
      render: (t) => (t.is_system ? 'Yes' : 'No'),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (t) => (
        <Button size="xs" variant="light" onClick={() => setModal({ kind: 'edit', type: t })}>
          Edit template
        </Button>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Institution Types"
        subtitle="Shared platform catalog of institution types."
        actions={
          <Button onClick={() => setModal({ kind: 'create' })}>
            New type
          </Button>
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <Text size="xs" c="dimmed" mb="md">
        Deactivation is not exposed by the backend API in this build.
      </Text>

      <DataTable
        columns={columns}
        rows={typesQuery.data ?? []}
        getRowKey={(t) => t.id}
      />

      <Modal opened={modal?.kind === 'create'} onClose={() => setModal(null)} title="New institution type">
        <Stack>
          <TextInput
            label="Name ID (lookup UUID)"
            required
            value={form.name_id}
            onChange={(e) => setForm({ ...form, name_id: e.currentTarget.value })}
          />
          <TextInput
            label="Code"
            required
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.currentTarget.value })}
          />
          <Switch
            label="System type"
            checked={form.is_system}
            onChange={(e) => setForm({ ...form, is_system: e.currentTarget.checked })}
          />
          <Button
            loading={createMutation.isPending}
            onClick={() =>
              createMutation.mutate({
                name_id: form.name_id,
                code: form.code,
                is_system: form.is_system,
                default_org_unit_template: null,
              })
            }
          >
            Create
          </Button>
        </Stack>
      </Modal>

      <Modal opened={modal?.kind === 'edit'} onClose={() => setModal(null)} title="Edit org-unit template">
        <Text size="sm" c="dimmed" mb="md">
          Update the default org-unit tree template (JSON).
        </Text>
        <Button
          loading={editMutation.isPending}
          onClick={() => {
            const type = modal?.kind === 'edit' ? modal.type : null;
            if (type) editMutation.mutate({ id: type.id, template: type.default_org_unit_template });
          }}
        >
          Save
        </Button>
      </Modal>
    </>
  );
}
