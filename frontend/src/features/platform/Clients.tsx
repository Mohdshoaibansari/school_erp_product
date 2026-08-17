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
import { platformApi } from '../../core/api/platform';
import type {
  ClientCreateDTO,
  ClientDTO,
  ClientUpdateDTO,
} from '../../core/api/dto/platform';
import { lookupsApi } from '../../core/api/lookups';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { usePermissions } from '../../core/access/usePermissions';
import { useNavigate } from 'react-router-dom';

type ModalState =
  | { kind: 'create' }
  | { kind: 'edit'; client: ClientDTO }
  | { kind: 'transition'; client: ClientDTO }
  | null;

const LIFECYCLE_STATES = ['active', 'suspended', 'archived'];

export function Clients() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { can } = usePermissions();
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);

  const [form, setForm] = useState({
    slug: '',
    display_name: '',
    legal_name: '',
    legal_entity_type_id: '',
    primary_contact_email: '',
  });
  const [transitionState, setTransitionState] = useState<string | null>(null);
  const [transitionReason, setTransitionReason] = useState('');

  const clientsQuery = useQuery({
    queryKey: ['platform', 'clients'],
    queryFn: () => platformApi.listClients().then((r) => r.data),
  });

  const legalEntityTypesQuery = useQuery({
    queryKey: ['lookups', 'legal-entity-types'],
    queryFn: () => lookupsApi.listLegalEntityTypes().then((r) => r.data),
    enabled: modal?.kind === 'create',
  });

  const filtered = useMemo(() => {
    const term = search.toLowerCase();
    return (clientsQuery.data ?? []).filter(
      (c) =>
        c.display_name.toLowerCase().includes(term) ||
        c.slug.toLowerCase().includes(term) ||
        c.legal_name.toLowerCase().includes(term),
    );
  }, [clientsQuery.data, search]);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['platform', 'clients'] });

  const createMutation = useMutation({
    mutationFn: (payload: ClientCreateDTO) =>
      platformApi.createClient(payload).then((r) => r.data),
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
    mutationFn: (vars: { id: string; payload: ClientUpdateDTO }) =>
      platformApi.updateClient(vars.id, vars.payload).then((r) => r.data),
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
      platformApi
        .transitionClient(vars.id, {
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
    setForm({
      slug: '',
      display_name: '',
      legal_name: '',
      legal_entity_type_id: '',
      primary_contact_email: '',
    });
  }

  function openCreate() {
    resetForm();
    setForbidden(null);
    setModal({ kind: 'create' });
  }

  function openEdit(client: ClientDTO) {
    setForm({
      slug: client.slug,
      display_name: client.display_name,
      legal_name: client.legal_name,
      legal_entity_type_id: client.legal_entity_type_id,
      primary_contact_email: client.primary_contact_email,
    });
    setForbidden(null);
    setModal({ kind: 'edit', client });
  }

  function openTransition(client: ClientDTO) {
    setTransitionState(client.current_lifecycle_status);
    setTransitionReason('');
    setForbidden(null);
    setModal({ kind: 'transition', client });
  }

  const columns: DataTableColumn<ClientDTO>[] = [
    {
      key: 'display_name',
      header: 'Client',
      render: (c) => c.display_name,
    },
    { key: 'slug', header: 'Slug', render: (c) => c.slug, hideBelow: 640 },
    {
      key: 'legal_name',
      header: 'Legal name',
      render: (c) => c.legal_name,
      hideBelow: 900,
    },
    {
      key: 'status',
      header: 'Status',
      render: (c) => <StatusPill status={c.current_lifecycle_status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (c) => (
        <Group gap="xs" wrap="nowrap">
          <Button
            size="xs"
            variant="light"
            onClick={() => navigate(`/platform/clients/${c.id}`)}
          >
            Users
          </Button>
          <Button size="xs" variant="light" onClick={() => openEdit(c)}>
            Edit
          </Button>
          {can('platform_owner') ? (
            <Button size="xs" variant="light" onClick={() => openTransition(c)}>
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
        title="Clients"
        subtitle="Manage platform clients and their lifecycle."
        actions={
          <Group>
            <TextInput
              placeholder="Search clients"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              data-testid="clients-search"
            />
            {can('platform_owner') ? (
              <Button onClick={openCreate} data-testid="clients-create">
                New client
              </Button>
            ) : null}
          </Group>
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <DataTable columns={columns} rows={filtered} getRowKey={(c) => c.id} />

      <Modal
        opened={modal?.kind === 'create'}
        onClose={() => setModal(null)}
        title="New client"
      >
        <Stack>
          <TextInput
            label="Slug"
            required
            value={form.slug}
            onChange={(e) => setForm({ ...form, slug: e.currentTarget.value })}
          />
          <TextInput
            label="Display name"
            required
            value={form.display_name}
            onChange={(e) =>
              setForm({ ...form, display_name: e.currentTarget.value })
            }
          />
          <TextInput
            label="Legal name"
            required
            value={form.legal_name}
            onChange={(e) =>
              setForm({ ...form, legal_name: e.currentTarget.value })
            }
          />
          <Select
            label="Legal entity type"
            searchable
            data={(legalEntityTypesQuery.data ?? []).map((t) => ({
              value: t.id,
              label: t.name,
            }))}
            value={form.legal_entity_type_id || null}
            onChange={(v) =>
              setForm({ ...form, legal_entity_type_id: v ?? '' })
            }
          />
          <TextInput
            label="Primary contact email"
            required
            type="email"
            value={form.primary_contact_email}
            onChange={(e) =>
              setForm({ ...form, primary_contact_email: e.currentTarget.value })
            }
          />
          <Button
            loading={createMutation.isPending}
            onClick={() =>
              createMutation.mutate({
                slug: form.slug,
                display_name: form.display_name,
                legal_name: form.legal_name,
                legal_entity_type_id: form.legal_entity_type_id,
                primary_contact_email: form.primary_contact_email,
                tax_registration_number: null,
                primary_contact_phone: null,
                billing_contact_email: null,
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
        title="Edit client"
      >
        <Stack>
          <TextInput
            label="Display name"
            value={form.display_name}
            onChange={(e) =>
              setForm({ ...form, display_name: e.currentTarget.value })
            }
          />
          <TextInput
            label="Legal name"
            value={form.legal_name}
            onChange={(e) =>
              setForm({ ...form, legal_name: e.currentTarget.value })
            }
          />
          <TextInput
            label="Primary contact email"
            value={form.primary_contact_email}
            onChange={(e) =>
              setForm({ ...form, primary_contact_email: e.currentTarget.value })
            }
          />
          <Button
            loading={updateMutation.isPending}
            onClick={() => {
              const client = modal?.kind === 'edit' ? modal.client : null;
              if (client) {
                updateMutation.mutate({
                  id: client.id,
                  payload: {
                    display_name: form.display_name,
                    legal_name: form.legal_name,
                    primary_contact_email: form.primary_contact_email,
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
        opened={modal?.kind === 'transition'}
        onClose={() => setModal(null)}
        title="Transition client"
      >
        <Stack>
          <Select
            label="New state"
            data={LIFECYCLE_STATES}
            value={transitionState}
            onChange={(v) => setTransitionState(v)}
          />
          <TextInput
            label="Reason"
            value={transitionReason}
            onChange={(e) => setTransitionReason(e.currentTarget.value)}
          />
          <Button
            loading={transitionMutation.isPending}
            onClick={() => {
              const client = modal?.kind === 'transition' ? modal.client : null;
              if (client && transitionState) {
                transitionMutation.mutate({
                  id: client.id,
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
