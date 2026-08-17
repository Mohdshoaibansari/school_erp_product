import { useState } from 'react';
import {
  Alert,
  Anchor,
  Button,
  Center,
  Container,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '../../core/api/auth';
import { normalizeApiError } from '../../core/api/errors';

export function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const resetToken = searchParams.get('token');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [requested, setRequested] = useState(false);
  const [loading, setLoading] = useState(false);

  const requestReset = async () => {
    setLoading(true);
    setError('');
    try {
      await authApi.requestPasswordReset({ email });
      setRequested(true);
    } catch (err) {
      setError(normalizeApiError(err).message || 'Could not send reset email');
    } finally {
      setLoading(false);
    }
  };

  const confirmReset = async () => {
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    if (!resetToken) {
      setError('Reset token is missing');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authApi.confirmPasswordReset({
        token: resetToken,
        new_password: password,
      });
      navigate('/login', { replace: true, state: { resetSuccess: true } });
    } catch (err) {
      setError(normalizeApiError(err).message || 'Reset failed');
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
              {resetToken ? 'Set new password' : 'Reset password'}
            </Title>
            <Text c="dimmed" size="sm" ta="center">
              {resetToken
                ? 'Choose a new password for your account.'
                : "Enter your email and we'll send a reset link."}
            </Text>

            {error ? <Alert color="danger">{error}</Alert> : null}

            {!resetToken && requested ? (
              <Alert color="success" title="Check your email">
                If an account exists for that email, a reset link has been sent.
              </Alert>
            ) : null}

            {!resetToken && !requested && (
              <Stack>
                <TextInput
                  label="Email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.currentTarget.value)}
                  data-testid="reset-email"
                />
                <Button loading={loading} onClick={() => void requestReset()}>
                  Send reset link
                </Button>
              </Stack>
            )}

            {resetToken && (
              <Stack>
                <PasswordInput
                  label="New password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.currentTarget.value)}
                  data-testid="reset-password"
                />
                <PasswordInput
                  label="Confirm password"
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.currentTarget.value)}
                  data-testid="reset-confirm"
                />
                <Button loading={loading} onClick={() => void confirmReset()}>
                  Set password
                </Button>
              </Stack>
            )}

            {!resetToken ? (
              <Anchor component={Link} to="/login" size="sm" ta="center">
                Back to sign in
              </Anchor>
            ) : null}
          </Stack>
        </Paper>
      </Container>
    </Center>
  );
}
