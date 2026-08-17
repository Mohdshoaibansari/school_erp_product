import { useState } from 'react';
import {
  Button,
  Group,
  Modal,
  Stack,
  Switch,
  TextInput,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { feesApi } from '../../core/api/fees';
import type {
  FeeTypeCreateDTO,
  FeeTypeDTO,
  FeeTypeUpdateDTO,
} from '../../core/api/dto/fees';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';
import { usePermissions } from '../../core/access/usePermissions';

type ModalState =
  | { kind: 'create' }
  | { kind: 'edit'; feeType: FeeTypeDTO }
  | null;

export function FeeTypes() {
  const { institutionId } = useTenant();
  const { can } = usePermissions();
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    description: '',
    default_amount: '',
    is_active: true,
  });

  const feeTypesQuery = useQuery({
    queryKey: ['fee-types', institutionId],
    queryFn: () => feesApi.listFeeTypes().then((r) => r.data),
    enabled: !!institutionId,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['fee-types', institutionId] });

  const createMutation = useMutation({
    mutationFn: (payload: FeeTypeCreateDTO) =>
      feesApi.createFeeType(payload).then((r) => r.data),
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
    mutationFn: (vars: { id: string; payload: FeeTypeUpdateDTO }) =>
      feesApi.updateFeeType(vars.id, vars.payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (feeTypeId: string) => feesApi.deleteFeeType(feeTypeId),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  function resetForm() {
    setForm({ name: '', description: '', default_amount: '', is_active: true });
  }

  function openCreate() {
    resetForm();
    setForbidden(null);
    setModal({ kind: 'create' });
  }

  function openEdit(feeType: FeeTypeDTO) {
    setForm({
      name: feeType.name,
      description: feeType.description ?? '',
      default_amount: feeType.default_amount,
      is_active: feeType.is_active,
    });
    setForbidden(null);
    setModal({ kind: 'edit', feeType });
  }

  const columns: DataTableColumn<FeeTypeDTO>[] = [
    { key: 'name', header: 'Name', render: (t) => t.name },
    {
      key: 'description',
      header: 'Description',
      render: (t) => t.description ?? '—',
      hideBelow: 900,
    },
    {
      key: 'default_amount',
      header: 'Default amount',
      render: (t) => t.default_amount,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (t) => (
        <StatusPill status={t.is_active ? 'active' : 'inactive'} />
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (t) => (
        <Group gap="xs" wrap="nowrap">
          <Button size="xs" variant="light" onClick={() => openEdit(t)}>
            Edit
          </Button>
          {can('institution_admin') ? (
            <Button
              size="xs"
              variant="light"
              color="danger"
              onClick={() => deactivateMutation.mutate(t.id)}
            >
              Deactivate
            </Button>
          ) : null}
        </Group>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Fee types"
        subtitle="Institution-scoped fee types and their default amounts."
        actions={
          can('institution_admin') ? (
            <Button onClick={openCreate}>New fee type</Button>
          ) : null
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <DataTable
        columns={columns}
        rows={feeTypesQuery.data ?? []}
        getRowKey={(t) => t.id}
      />

      <Modal
        opened={modal?.kind === 'create'}
        onClose={() => setModal(null)}
        title="New fee type"
      >
        <Stack>
          <TextInput
            label="Name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <TextInput
            label="Description"
            value={form.description}
            onChange={(e) =>
              setForm({ ...form, description: e.currentTarget.value })
            }
          />
          <TextInput
            label="Default amount"
            required
            inputMode="decimal"
            value={form.default_amount}
            onChange={(e) =>
              setForm({ ...form, default_amount: e.currentTarget.value })
            }
          />
          <Button
            loading={createMutation.isPending}
            disabled={!form.name || !form.default_amount}
            onClick={() =>
              createMutation.mutate({
                name: form.name,
                description: form.description || null,
                default_amount: form.default_amount,
                institution_id: institutionId ?? '',
              })
            }
          >
            Create
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={modal?.kind === 'edit'}
        onClose={() => setModal(null)}
        title="Edit fee type"
      >
        <Stack>
          <TextInput
            label="Name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <TextInput
            label="Description"
            value={form.description}
            onChange={(e) =>
              setForm({ ...form, description: e.currentTarget.value })
            }
          />
          <TextInput
            label="Default amount"
            required
            inputMode="decimal"
            value={form.default_amount}
            onChange={(e) =>
              setForm({ ...form, default_amount: e.currentTarget.value })
            }
          />
          <Switch
            label="Active"
            checked={form.is_active}
            onChange={(e) =>
              setForm({ ...form, is_active: e.currentTarget.checked })
            }
          />
          <Button
            loading={updateMutation.isPending}
            disabled={!form.name || !form.default_amount}
            onClick={() => {
              const feeType = modal?.kind === 'edit' ? modal.feeType : null;
              if (feeType) {
                updateMutation.mutate({
                  id: feeType.id,
                  payload: {
                    name: form.name,
                    description: form.description || null,
                    default_amount: form.default_amount,
                    is_active: form.is_active,
                  },
                });
              }
            }}
          >
            Save
          </Button>
        </Stack>
      </Modal>
    </>
  );
}
