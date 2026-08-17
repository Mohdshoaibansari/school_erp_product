import { Component, type ReactNode } from 'react';
import { Button, Center, Stack, Text, Title } from '@mantine/core';

interface Props {
  fallback?: ReactNode;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches render errors and shows a friendly fallback instead of a blank page.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Center h="60vh" px="md">
          <Stack align="center" gap="sm">
            <Title order={3}>Something went wrong</Title>
            <Text c="dimmed" size="sm" ta="center" maw={420}>
              {this.state.error?.message ?? 'An unexpected error occurred.'}
            </Text>
            <Button variant="light" onClick={this.handleReload} mt="sm">
              Reload
            </Button>
          </Stack>
        </Center>
      );
    }

    return this.props.children;
  }
}
