import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Paper, Title, TextInput, PasswordInput, Button, Stack, Alert } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import api from '../api/client';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.post('/v1/auth/login', { email, password });
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      notifications.show({ title: 'Logged in', message: 'Welcome!', color: 'green' });
      navigate('/fees');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally { setLoading(false); }
  };

  return (
    <Container size={420} mt={100}>
      <Paper p="xl" radius="md" withBorder>
        <Title order={2} ta="center" mb="lg">School ERP Login</Title>
        {error && <Alert color="red" mb="md">{error}</Alert>}
        <Stack>
          <TextInput label="Email" value={email} onChange={(e) => setEmail(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleLogin()} />
          <PasswordInput label="Password" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleLogin()} />
          <Button fullWidth loading={loading} onClick={handleLogin}>Login</Button>
        </Stack>
      </Paper>
    </Container>
  );
}
