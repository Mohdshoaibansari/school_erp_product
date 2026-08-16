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
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../../core/api/auth';
import { normalizeApiError } from '../../core/api/errors';
import { useSession } from '../../core/auth/useSession';

interface LoginLocationState {
  from?: { pathname?: string };
  resetSuccess?: boolean;
}

export default function Login() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LoginLocationState;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event?: { preventDefault: () => void }) => {
    event?.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await authApi.login({ email, password });
      signIn(response.data);
      navigate(state.from?.pathname ?? '/', { replace: true });
    } catch (err) {
      setError(normalizeApiError(err).message || 'Login failed');
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
              Sign in
            </Title>
            <Text c="dimmed" size="sm" ta="center">
              School ERP management console
            </Text>

            {state.resetSuccess ? (
              <Alert color="success" title="Password reset">
                Your password was reset successfully. Please sign in.
              </Alert>
            ) : null}

            {error ? <Alert color="danger">{error}</Alert> : null}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                void handleSubmit();
              }}
            >
              <Stack>
                <TextInput
                  label="Email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.currentTarget.value)}
                  placeholder="you@school.example"
                  data-testid="login-email"
                />
                <PasswordInput
                  label="Password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.currentTarget.value)}
                  placeholder="Your password"
                  data-testid="login-password"
                />
                <Button
                  type="submit"
                  fullWidth
                  loading={loading}
                  data-testid="login-submit"
                >
                  Sign in
                </Button>
              </Stack>
            </form>

            <Anchor component={Link} to="/password/reset" size="sm" ta="center">
              Forgot password?
            </Anchor>
          </Stack>
        </Paper>
      </Container>
    </Center>
  );
}
