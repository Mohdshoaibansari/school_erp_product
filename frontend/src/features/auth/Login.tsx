import { useState } from 'react';
import { Alert, Anchor, Button, Center, Container, PasswordInput, Stack, Text, TextInput, Title, Box, Group } from '@mantine/core';
import { ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../../core/api/auth';
import { normalizeApiError } from '../../core/api/errors';
import { useSession } from '../../core/auth/useSession';

interface LoginLocationState { from?: { pathname?: string }; resetSuccess?: boolean; }

export function Login() {
  const { signIn } = useSession(); const navigate = useNavigate(); const location = useLocation();
  const state = (location.state ?? {}) as LoginLocationState;
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [error, setError] = useState(''); const [loading, setLoading] = useState(false);
  const handleSubmit = async (event?: { preventDefault: () => void }) => {
    event?.preventDefault(); setLoading(true); setError('');
    try { const response = await authApi.login({ email, password }); signIn(response.data); navigate(state.from?.pathname ?? '/', { replace: true }); }
    catch (err) { setError(normalizeApiError(err).message || 'Login failed'); }
    finally { setLoading(false); }
  };

  return (
    <Box style={{ minHeight: '100vh', background: '#FAFAFA', display: 'grid', gridTemplateColumns: 'minmax(0,1.05fr) minmax(420px,.95fr)' }} className="login-shell">
      <Box visibleFrom="md" style={{ background: '#0F172A', position: 'relative', overflow: 'hidden', color: '#fff', padding: 'clamp(40px,7vw,100px)' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 70% 20%, rgba(0,82,255,.25), transparent 35%), radial-gradient(circle at 20% 90%, rgba(77,124,255,.15), transparent 30%)' }} />
        <div style={{ position: 'absolute', inset: 0, opacity: .05, backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)', backgroundSize: '32px 32px' }} />
        <Stack style={{ position: 'relative', height: '100%' }} justify="space-between">
          <Group gap="sm"><Center style={{ width: 44, height: 44, borderRadius: 14, background: 'linear-gradient(135deg,#0052FF,#4D7CFF)', boxShadow: '0 12px 28px rgba(0,82,255,.32)' }}><Sparkles size={21} /></Center><div><Text fw={700}>School ERP</Text><Text size="xs" c="#94A3B8" style={{ fontFamily: 'JetBrains Mono', letterSpacing: '.12em' }}>ADMINISTRATION PLATFORM</Text></div></Group>
          <Stack gap="xl" maw={600}><div className="erp-section-label" style={{ color: '#8FB0FF', borderColor: 'rgba(143,176,255,.25)', background: 'rgba(0,82,255,.08)' }}>Secure workspace</div><Title order={1} c="white" style={{ fontSize: 'clamp(3rem,5vw,5rem)', lineHeight: 1.02 }}>Run your school with <span className="erp-gradient-text">clarity.</span></Title><Text c="#CBD5E1" size="lg" lh={1.7} maw={520}>A focused management workspace for institutions, people, academics, finance and learning.</Text><Group gap="sm"><ShieldCheck size={18} color="#4D7CFF" /><Text size="sm" c="#CBD5E1">Role-aware access • Secure sessions • Institution-scoped data</Text></Group></Stack>
          <Text size="xs" c="#64748B">School ERP · Administration workspace</Text>
        </Stack>
      </Box>
      <Center px={{ base: 'lg', sm: 'xl' }} py="xl"><Container size={460} w="100%"><Stack gap="xl"><div><Text className="erp-section-label">Welcome back</Text><Title order={2} mt="md" style={{ fontSize: 'clamp(2.1rem,5vw,3.1rem)' }}>Sign in to your <span className="erp-gradient-text">workspace</span></Title><Text c="dimmed" mt="xs" lh={1.6}>Use your School ERP account to continue.</Text></div>
        {state.resetSuccess ? <Alert color="success" title="Password reset">Your password was reset successfully. Please sign in.</Alert> : null}
        {error ? <Alert color="danger">{error}</Alert> : null}
        <form onSubmit={(e) => { e.preventDefault(); void handleSubmit(); }}><Stack gap="md"><TextInput label="Email" type="email" required value={email} onChange={(e) => setEmail(e.currentTarget.value)} placeholder="you@school.example" data-testid="login-email" /><PasswordInput label="Password" required value={password} onChange={(e) => setPassword(e.currentTarget.value)} placeholder="Your password" data-testid="login-password" /><Button type="submit" fullWidth loading={loading} rightSection={<ArrowRight size={17} />} data-testid="login-submit">Sign in</Button></Stack></form>
        <Group justify="space-between"><Anchor component={Link} to="/password/reset" size="sm">Forgot password?</Anchor><Text size="xs" c="dimmed">Protected workspace</Text></Group>
      </Stack></Container></Center>
    </Box>
  );
}
