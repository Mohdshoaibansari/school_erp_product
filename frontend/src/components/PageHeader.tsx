import { Group, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

export function PageHeader({ title, subtitle, actions, eyebrow }: { title: string; subtitle?: string; actions?: ReactNode; eyebrow?: string }) {
  return (
    <div className="erp-page-header" style={{ marginBottom: 26 }}>
      <Group justify="space-between" align="flex-end" gap="xl" wrap="wrap">
        <Stack gap={8}>
          <div className="erp-section-label">{eyebrow ?? 'Workspace'}</div>
          <Title order={1} style={{ fontSize: 'clamp(2rem, 4vw, 3rem)', letterSpacing: '-.025em' }}>{title}</Title>
          {subtitle ? <Text c="dimmed" size="sm" maw={680} lh={1.6}>{subtitle}</Text> : null}
        </Stack>
        {actions ? <Group gap="sm" align="flex-end">{actions}</Group> : null}
      </Group>
    </div>
  );
}
