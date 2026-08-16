import { Group, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-start" mb="md">
      <div>
        <Title order={2}>{title}</Title>
        {subtitle ? (
          <Text c="dimmed" size="sm">
            {subtitle}
          </Text>
        ) : null}
      </div>
      {actions ? <Group gap="sm">{actions}</Group> : null}
    </Group>
  );
}
