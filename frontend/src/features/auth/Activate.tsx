import { useState } from 'react';
import {
  Alert,
  Button,
  Center,
  Container,
  Paper,
  PasswordInput,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '../../core/api/auth';
import { normalizeApiError } from '../../core/api/errors';

export default function Activate() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inviteToken = searchParams.get('token') ?? '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event?: { preventDefault: () => void }) => {
    event?.preventDefault();
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authApi.activate({ invite_token: inviteToken, password });
      navigate('/login', { replace: true });
    } catch (err) {
      setError(normalizeApiError(err).message || 'Activation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Center h="100vh" px="md">
      <Container size={420} w="100%">
        <Paper withBorder p="xl" radius="lg">
          <Stack>
            <Title order={2} ta="center">
              Activate account
            </Title>
            <Text c="dimmed" size="sm" ta="center">
              Set a password to activate your account.
            </Text>

            {error ? <Alert color="danger">{error}</Alert> : null}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                void handleSubmit();
              }}
            >
              <Stack>
                <PasswordInput
                  label="New password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.currentTarget.value)}
                  data-testid="activate-password"
                />
                <PasswordInput
                  label="Confirm password"
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.currentTarget.value)}
                  data-testid="activate-confirm"
                />
                <Button type="submit" fullWidth loading={loading}>
                  Activate
                </Button>
              </Stack>
            </form>
          </Stack>
        </Paper>
      </Container>
    </Center>
  );
}
