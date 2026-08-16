import { useState } from 'react';
import {
  Alert,
  Button,
  Center,
  Container,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { authApi } from '../../core/api/auth';
import { normalizeApiError } from '../../core/api/errors';

type Step = 'request' | 'verify' | 'done';

export default function OtpVerify() {
  const [step, setStep] = useState<Step>('request');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const requestOtp = async () => {
    setLoading(true);
    setError('');
    try {
      await authApi.requestOtp({ email });
      setStep('verify');
    } catch (err) {
      setError(normalizeApiError(err).message || 'Could not send OTP');
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    setLoading(true);
    setError('');
    try {
      await authApi.verifyOtp({ email, token: otp });
      setStep('done');
    } catch (err) {
      setError(normalizeApiError(err).message || 'Invalid or expired code');
      setOtp('');
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
              Verify code
            </Title>
            <Text c="dimmed" size="sm" ta="center">
              Enter the one-time code sent to your email.
            </Text>

            {error ? <Alert color="danger">{error}</Alert> : null}

            {step === 'request' && (
              <Stack>
                <TextInput
                  label="Email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.currentTarget.value)}
                  data-testid="otp-email"
                />
                <Button loading={loading} onClick={() => void requestOtp()}>
                  Send code
                </Button>
              </Stack>
            )}

            {step === 'verify' && (
              <Stack align="center">
                <TextInput
                  label="Code"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.currentTarget.value)}
                  data-testid="otp-input"
                />
                <Button loading={loading} onClick={() => void verifyOtp()}>
                  Verify
                </Button>
                <Button variant="subtle" onClick={() => void requestOtp()}>
                  Re-send code
                </Button>
              </Stack>
            )}

            {step === 'done' && (
              <Alert color="success" title="Verified">
                Your code was verified successfully.
              </Alert>
            )}
          </Stack>
        </Paper>
      </Container>
    </Center>
  );
}
