import { Button, Card, Container, Stack, Text, Title } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import type { ApiError } from '../core/api/errors';

/**
 * Friendly permission-denied surface (R8, REQ-SHELL-07). Never renders a raw
 * error or stack trace. Used full-page for route-level denials and re-used
 * by the inline action-level surface.
 */
export function Forbidden({ error }: { error?: ApiError }) {
  const navigate = useNavigate();

  return (
    <Container size={480} py="xl">
      <Card withBorder padding="xl" ta="center">
        <Stack align="center">
          <Title order={3}>You don't have permission</Title>
          <Text c="dimmed" size="sm">
            {error?.message ??
              'Your role does not allow access to this area. Contact an administrator if you believe this is a mistake.'}
          </Text>
          <Button variant="light" onClick={() => navigate(-1)}>
            Go back
          </Button>
        </Stack>
      </Card>
    </Container>
  );
}
