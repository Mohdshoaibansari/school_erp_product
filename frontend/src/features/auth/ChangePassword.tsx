import { useState } from 'react';
import {
  Alert,
  Button,
  PasswordInput,
  Stack,
  Text,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { authApi } from '../../core/api/auth';
import { normalizeApiError } from '../../core/api/errors';
import { FormCard } from '../../components/FormCard';
import { PageHeader } from '../../components/PageHeader';

export function ChangePassword() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event?: { preventDefault: () => void }) => {
    event?.preventDefault();
    if (next !== confirm) {
      setError('New passwords do not match');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authApi.changePassword({
        current_password: current,
        new_password: next,
      });
      notifications.show({
        title: 'Password changed',
        message: 'Your password was updated successfully.',
        color: 'success',
      });
      setCurrent('');
      setNext('');
      setConfirm('');
    } catch (err) {
      setError(normalizeApiError(err).message || 'Could not change password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader title="Change password" />
      <FormCard>
        <Text size="sm" c="dimmed" mb="md">
          Choose a new password for your account.
        </Text>
        {error ? <Alert color="danger" mb="md">{error}</Alert> : null}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <Stack maw={420}>
            <PasswordInput
              label="Current password"
              required
              value={current}
              onChange={(e) => setCurrent(e.currentTarget.value)}
              data-testid="change-current"
            />
            <PasswordInput
              label="New password"
              required
              value={next}
              onChange={(e) => setNext(e.currentTarget.value)}
              data-testid="change-new"
            />
            <PasswordInput
              label="Confirm new password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.currentTarget.value)}
              data-testid="change-confirm"
            />
            <Button type="submit" loading={loading}>
              Update password
            </Button>
          </Stack>
        </form>
      </FormCard>
    </>
  );
}
