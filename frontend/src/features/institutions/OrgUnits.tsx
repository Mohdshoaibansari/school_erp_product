import { useMemo, useState } from 'react';
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
import { institutionsApi } from '../../core/api/institutions';
import { lookupsApi } from '../../core/api/lookups';
import type {
  OrgUnitCreateDTO,
  OrgUnitDTO,
} from '../../core/api/dto/institutions';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';

interface TreeNode {
  unit: OrgUnitDTO;
  children: TreeNode[];
}

function buildTree(units: OrgUnitDTO[]): TreeNode[] {
  const byParent = new Map<string | null, OrgUnitDTO[]>();
  for (const unit of units) {
    const key = unit.parent_id;
    const list = byParent.get(key) ?? [];
    list.push(unit);
    byParent.set(key, list);
  }
  const sort = (list: OrgUnitDTO[]) =>
    [...list].sort((a, b) => a.sort_order - b.sort_order);

  const walk = (parentId: string | null): TreeNode[] =>
    sort(byParent.get(parentId) ?? []).map((unit) => ({
      unit,
      children: walk(unit.id),
    }));

  return walk(null);
}

type ModalState =
  | { kind: 'create'; parentId: string | null }
  | { kind: 'move'; unit: OrgUnitDTO }
  | { kind: 'reorder'; unit: OrgUnitDTO }
  | null;

export default function OrgUnits() {
  const { institutionId = '' } = useParams();
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({ parent_id: '', name: '', type_id: '', sort_order: '0' });
  const [moveParentId, setMoveParentId] = useState('');
  const [reorderValue, setReorderValue] = useState('0');

  const orgUnitsQuery = useQuery({
    queryKey: ['org-units', institutionId],
    queryFn: () => institutionsApi.listOrgUnits(institutionId).then((r) => r.data),
    enabled: !!institutionId,
  });

  const typesQuery = useQuery({
    queryKey: ['lookups', 'org-unit-types'],
    queryFn: () => lookupsApi.listOrgUnitTypes().then((r) => r.data),
    enabled: modal?.kind === 'create',
  });

  const tree = useMemo(
    () => buildTree(orgUnitsQuery.data ?? []),
    [orgUnitsQuery.data],
  );

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['org-units', institutionId] });

  const createMutation = useMutation({
    mutationFn: (payload: OrgUnitCreateDTO) =>
      institutionsApi.createOrgUnit(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const moveMutation = useMutation({
    mutationFn: (vars: { id: string; new_parent_id: string | null }) =>
      institutionsApi.moveOrgUnit(vars.id, { new_parent_id: vars.new_parent_id }).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const reorderMutation = useMutation({
    mutationFn: (vars: { id: string; sort_order: number }) =>
      institutionsApi.reorderOrgUnit(vars.id, { sort_order: vars.sort_order }).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (unit: OrgUnitDTO) =>
      institutionsApi.archiveOrgUnit(unit.id).then((r) => r.data),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: (unit: OrgUnitDTO) =>
      institutionsApi.reactivateOrgUnit(unit.id).then((r) => r.data),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  function renderNode(node: TreeNode, depth: number) {
    const { unit } = node;
    return (
      <div key={unit.id}>
        <Group
          justify="space-between"
          py="xs"
          pl={depth * 20}
          style={{ borderBottom: '1px solid #e5e7eb' }}
        >
          <Group gap="xs">
            <Text fw={500}>{unit.name}</Text>
            <StatusPill status={unit.current_lifecycle_status} />
            <Text size="xs" c="dimmed">
              order {unit.sort_order}
            </Text>
          </Group>
          <Group gap="xs" wrap="nowrap">
            <Button
              size="xs"
              variant="light"
              onClick={() => {
                setForm({ parent_id: unit.id, name: '', type_id: '', sort_order: '0' });
                setModal({ kind: 'create', parentId: unit.id });
              }}
            >
              Add child
            </Button>
            <Button size="xs" variant="light" onClick={() => {
              setMoveParentId(unit.parent_id ?? '');
              setModal({ kind: 'move', unit });
            }}>
              Move
            </Button>
            <Button size="xs" variant="light" onClick={() => {
              setReorderValue(String(unit.sort_order));
              setModal({ kind: 'reorder', unit });
            }}>
              Reorder
            </Button>
            {unit.current_lifecycle_status === 'archived' ? (
              <Button size="xs" color="success" onClick={() => reactivateMutation.mutate(unit)}>
                Reactivate
              </Button>
            ) : (
              <Button size="xs" color="danger" onClick={() => archiveMutation.mutate(unit)}>
                Archive
              </Button>
            )}
          </Group>
        </Group>
        {node.children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  }

  return (
    <>
      <PageHeader
        title="Org Units"
        subtitle="Organisation unit tree for this institution."
        actions={
          <Button
            onClick={() => {
              setForm({ parent_id: '', name: '', type_id: '', sort_order: '0' });
              setModal({ kind: 'create', parentId: null });
            }}
          >
            New org unit
          </Button>
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <div data-testid="org-unit-tree">
        {tree.length === 0 ? (
          <Text c="dimmed" py="md">
            No org units yet.
          </Text>
        ) : (
          tree.map((node) => renderNode(node, 0))
        )}
      </div>

      <Modal opened={modal?.kind === 'create'} onClose={() => setModal(null)} title="New org unit">
        <Stack>
          <TextInput
            label="Name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <Select
            label="Type"
            searchable
            data={(typesQuery.data ?? []).map((t) => ({ value: t.id, label: t.name }))}
            value={form.type_id || null}
            onChange={(v) => setForm({ ...form, type_id: v ?? '' })}
          />
          <TextInput
            label="Sort order"
            value={form.sort_order}
            onChange={(e) => setForm({ ...form, sort_order: e.currentTarget.value })}
          />
          <Button
            loading={createMutation.isPending}
            onClick={() =>
              createMutation.mutate({
                institution_id: institutionId,
                parent_id: form.parent_id || null,
                name: form.name,
                type_id: form.type_id,
                sort_order: Number(form.sort_order) || 0,
                code: null,
              })
            }
          >
            Create
          </Button>
        </Stack>
      </Modal>

      <Modal opened={modal?.kind === 'move'} onClose={() => setModal(null)} title="Move org unit">
        <Stack>
          <TextInput
            label="New parent ID (blank for root)"
            value={moveParentId}
            onChange={(e) => setMoveParentId(e.currentTarget.value)}
          />
          <Button
            loading={moveMutation.isPending}
            onClick={() => {
              const unit = modal?.kind === 'move' ? modal.unit : null;
              if (unit) moveMutation.mutate({ id: unit.id, new_parent_id: moveParentId || null });
            }}
          >
            Move
          </Button>
        </Stack>
      </Modal>

      <Modal opened={modal?.kind === 'reorder'} onClose={() => setModal(null)} title="Reorder org unit">
        <Stack>
          <TextInput
            label="New sort order"
            value={reorderValue}
            onChange={(e) => setReorderValue(e.currentTarget.value)}
          />
          <Button
            loading={reorderMutation.isPending}
            onClick={() => {
              const unit = modal?.kind === 'reorder' ? modal.unit : null;
              if (unit) reorderMutation.mutate({ id: unit.id, sort_order: Number(reorderValue) || 0 });
            }}
          >
            Save
          </Button>
        </Stack>
      </Modal>
    </>
  );
}
