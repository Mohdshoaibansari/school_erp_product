import { useState } from 'react';
import {
  Alert,
  Button,
  Checkbox,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { platformApi } from '../../core/api/platform';
import type {
  ApprovalDTO,
  OwnershipTransferEventDTO,
} from '../../core/api/dto/platform';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { PageHeader } from '../../components/PageHeader';
import { PermissionDenied } from '../../components/PermissionDenied';

export function OwnershipTransfers() {
  const [form, setForm] = useState({
    institution_id: '',
    to_client_id: '',
    reason: '',
  });
  const [consentSource, setConsentSource] = useState(false);
  const [consentDest, setConsentDest] = useState(false);
  const [approval, setApproval] = useState<ApprovalDTO | null>(null);
  const [event, setEvent] = useState<OwnershipTransferEventDTO | null>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [error, setError] = useState('');

  const initiateMutation = useMutation({
    mutationFn: () =>
      platformApi
        .requestOwnershipTransfer({
          institution_id: form.institution_id,
          to_client_id: form.to_client_id,
          reason: form.reason || null,
        })
        .then((r) => r.data),
    onSuccess: (data) => {
      setApproval(data);
      setEvent(null);
      setError('');
    },
    onError: (err) => {
      if (isForbidden(err)) {
        setForbidden(normalizeApiError(err).message);
      } else {
        setError(normalizeApiError(err).message);
      }
    },
  });

  const approveMutation = useMutation({
    mutationFn: () =>
      platformApi
        .approveOwnershipTransfer(
          approval?.id ?? '',
          form.to_client_id,
          {
            consent_source: consentSource,
            consent_dest: consentDest,
            reason: form.reason || null,
          },
        )
        .then((r) => r.data),
    onSuccess: (data) => {
      setEvent(data);
    },
    onError: (err) => {
      if (isForbidden(err)) {
        setForbidden(normalizeApiError(err).message);
      } else {
        setError(normalizeApiError(err).message);
      }
    },
  });

  return (
    <>
      <PageHeader
        title="Ownership Transfers"
        subtitle="Move an institution between client owners."
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}
      {error ? <Alert color="danger" mb="md">{error}</Alert> : null}

      <Paper withBorder p="lg" mb="lg" maw={520}>
        <Stack>
          <TextInput
            label="Institution ID"
            required
            value={form.institution_id}
            onChange={(e) => setForm({ ...form, institution_id: e.currentTarget.value })}
            data-testid="transfer-institution"
          />
          <TextInput
            label="Destination client ID"
            required
            value={form.to_client_id}
            onChange={(e) => setForm({ ...form, to_client_id: e.currentTarget.value })}
            data-testid="transfer-client"
          />
          <TextInput
            label="Reason"
            value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.currentTarget.value })}
          />
          <Button
            loading={initiateMutation.isPending}
            onClick={() => initiateMutation.mutate()}
            data-testid="transfer-initiate"
          >
            Initiate transfer
          </Button>
        </Stack>
      </Paper>

      {approval && !event ? (
        <Paper withBorder p="lg" maw={520}>
          <Text fw={600} mb="sm">
            Pending approval
          </Text>
          <Text size="sm" c="dimmed" mb="md">
            Approval #{approval.id} · status: {approval.status}
          </Text>
          <Stack>
            <Checkbox
              label="Source client consent"
              checked={consentSource}
              onChange={(e) => setConsentSource(e.currentTarget.checked)}
            />
            <Checkbox
              label="Destination client consent"
              checked={consentDest}
              onChange={(e) => setConsentDest(e.currentTarget.checked)}
            />
            <Group>
              <Button
                loading={approveMutation.isPending}
                onClick={() => approveMutation.mutate()}
                data-testid="transfer-approve"
              >
                Approve & execute
              </Button>
            </Group>
          </Stack>
        </Paper>
      ) : null}

      {event ? (
        <Alert color="success" title="Transfer complete">
          Institution {event.institution_id} transferred from {event.from_client_id} to{' '}
          {event.to_client_id}.
        </Alert>
      ) : null}
    </>
  );
}
