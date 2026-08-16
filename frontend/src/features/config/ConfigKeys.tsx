import { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Group,
  Modal,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { configApi } from '../../core/api/config';
import type {
  ConfigKeyDTO,
  ConfigValueDTO,
  ConfigValueType,
} from '../../core/api/dto/config';
import { normalizeApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { useTenant } from '../../core/context/useTenant';

function stringify(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

function valueToInput(type: ConfigValueType, value: unknown): string {
  if (value === null || value === undefined) return '';
  if (type === 'json') return JSON.stringify(value);
  return String(value);
}

/** Convert the type-aware input back into the typed value sent to the API. */
function inputToValue(type: ConfigValueType, text: string): unknown {
  if (type === 'number') return Number(text);
  if (type === 'boolean') return text === 'true';
  if (type === 'json') return JSON.parse(text);
  return text;
}

export default function ConfigKeys() {
  const { institutionId, clientId } = useTenant();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<ConfigKeyDTO | null>(null);
  const [textValue, setTextValue] = useState('');
  const [boolValue, setBoolValue] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const keysQuery = useQuery({
    queryKey: ['config-keys', institutionId],
    queryFn: () =>
      configApi
        .listKeys({ include_deprecated: true, page_size: 200 })
        .then((r) => r.data.items),
    enabled: !!institutionId,
  });

  const valuesQuery = useQuery({
    queryKey: ['config-values', institutionId],
    queryFn: () =>
      configApi
        .listValues({ page_size: 200 })
        .then((r) => r.data.items),
    enabled: !!institutionId,
  });

  const resolveQuery = useQuery({
    queryKey: ['config-resolve', institutionId, editing?.key],
    queryFn: () =>
      configApi
        .resolveKey(editing?.key ?? '', {
          institution_id: institutionId,
          client_id: clientId,
        })
        .then((r) => r.data),
    enabled: !!editing && !!institutionId,
  });

  const institutionValues = useMemo(() => {
    const map = new Map<string, ConfigValueDTO>();
    for (const v of valuesQuery.data ?? []) {
      if (v.scope_type === 'institution') map.set(v.key_id, v);
    }
    return map;
  }, [valuesQuery.data]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['config-keys', institutionId] });
    queryClient.invalidateQueries({ queryKey: ['config-values', institutionId] });
    queryClient.invalidateQueries({
      queryKey: ['config-resolve', institutionId],
    });
  };

  const saveMutation = useMutation({
    mutationFn: (vars: {
      key: ConfigKeyDTO;
      existing: ConfigValueDTO | undefined;
      value: unknown;
    }) => {
      if (vars.existing) {
        return configApi
          .updateValue(vars.existing.id, { value: vars.value })
          .then((r) => r.data);
      }
      return configApi
        .createValue({
          key_id: vars.key.id,
          scope_type: 'institution',
          scope_id: institutionId ?? '',
          value: vars.value,
        })
        .then((r) => r.data);
    },
    onSuccess: () => {
      invalidate();
      setEditing(null);
      setApiError(null);
      setFormError(null);
    },
    onError: (err) => {
      setApiError(normalizeApiError(err).message);
    },
  });

  function openEdit(key: ConfigKeyDTO) {
    const existing = institutionValues.get(key.id);
    setEditing(key);
    setTextValue(valueToInput(key.type, existing?.value ?? key.default_value));
    setBoolValue(existing?.value === true || (existing === undefined && key.default_value === true));
    setFormError(null);
    setApiError(null);
  }

  function submit() {
    if (!editing) return;
    let value: unknown;
    try {
      value =
        editing.type === 'boolean'
          ? boolValue
          : inputToValue(editing.type, textValue);
    } catch {
      setFormError('Enter a valid value for this key type.');
      return;
    }
    setFormError(null);
    saveMutation.mutate({
      key: editing,
      existing: institutionValues.get(editing.id),
      value,
    });
  }

  const columns: DataTableColumn<ConfigKeyDTO>[] = [
    { key: 'key', header: 'Key', render: (k) => k.key },
    { key: 'type', header: 'Type', render: (k) => k.type, hideBelow: 640 },
    {
      key: 'category',
      header: 'Category',
      render: (k) => k.category,
      hideBelow: 900,
    },
    {
      key: 'value',
      header: 'Institution value',
      render: (k) => {
        const v = institutionValues.get(k.id);
        const raw = v ? v.value : k.default_value;
        return stringify(raw) || '—';
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (k) => (
        <Button size="xs" variant="light" onClick={() => openEdit(k)}>
          Edit value
        </Button>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Configuration keys"
        subtitle="Institution-scoped configuration values."
      />

      <DataTable
        columns={columns}
        rows={keysQuery.data ?? []}
        getRowKey={(k) => k.id}
      />

      <Modal
        opened={!!editing}
        onClose={() => setEditing(null)}
        title={editing ? `Edit ${editing.key}` : ''}
      >
        {editing ? (
          <Stack>
            <Text size="sm" c="dimmed">
              {editing.description}
            </Text>
            <Alert color="blue" variant="light">
              <Text size="sm">
                Effective value:{' '}
                {resolveQuery.data
                  ? `${stringify(resolveQuery.data.resolved_value)} (source: ${resolveQuery.data.source_scope})`
                  : '…'}
              </Text>
            </Alert>

            {editing.type === 'boolean' ? (
              <Switch
                label="Value"
                checked={boolValue}
                onChange={(e) => setBoolValue(e.currentTarget.checked)}
              />
            ) : editing.type === 'json' ? (
              <Textarea
                label="Value (JSON)"
                autosize
                minRows={4}
                value={textValue}
                onChange={(e) => setTextValue(e.currentTarget.value)}
              />
            ) : (
              <TextInput
                label="Value"
                type={editing.type === 'number' ? 'number' : editing.type === 'date' ? 'date' : 'text'}
                value={textValue}
                onChange={(e) => setTextValue(e.currentTarget.value)}
              />
            )}

            {formError ? (
              <Alert color="danger" title="Invalid value">
                {formError}
              </Alert>
            ) : null}

            {apiError ? (
              <Alert color="danger" title="Update failed">
                {apiError}
              </Alert>
            ) : null}

            <Group justify="flex-end">
              <Button variant="default" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button loading={saveMutation.isPending} onClick={submit}>
                Save
              </Button>
            </Group>
          </Stack>
        ) : null}
      </Modal>
    </>
  );
}
