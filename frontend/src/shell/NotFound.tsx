import { Button, Card, Container, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <Container size={480} py="xl">
      <Card withBorder padding="xl" ta="center">
        <Stack align="center">
          <Title order={3}>Page not found</Title>
          <Text c="dimmed" size="sm">
            The page you are looking for does not exist.
          </Text>
          <Button component={Link} to="/" variant="light">
            Go home
          </Button>
        </Stack>
      </Card>
    </Container>
  );
}
