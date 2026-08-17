import { Button, Center, Paper, Stack, Text, Title } from '@mantine/core';
import { AlertCircle } from 'lucide-react';

/**
 * Friendly error surface with optional retry button.
 * - variant 'page' centres vertically for a full-page error.
 * - variant 'section' renders inline for a partial-section error.
 */
export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  variant = 'section',
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
  variant?: 'page' | 'section';
}) {
  const content = (
    <Paper withBorder p="xl" radius="md" maw={480} mx={variant === 'page' ? 'auto' : undefined}>
      <Stack align="center" gap="sm">
        <AlertCircle size={40} color="var(--mantine-color-danger-6)" />
        <Title order={4}>{title}</Title>
        <Text c="dimmed" size="sm" ta="center">
          {message}
        </Text>
        {onRetry ? (
          <Button variant="light" onClick={onRetry} mt="sm">
            Try Again
          </Button>
        ) : null}
      </Stack>
    </Paper>
  );

  if (variant === 'page') {
    return (
      <Center h="60vh" px="md">
        {content}
      </Center>
    );
  }

  return content;
}
