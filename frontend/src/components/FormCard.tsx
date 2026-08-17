import { Card, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';

export function FormCard({ title, children, footer }: { title?: string; children: ReactNode; footer?: ReactNode }) {
  return <Card className="erp-card" withBorder={false} padding="xl" radius="lg"><Stack gap="lg">{title ? <Text fw={650} size="lg">{title}</Text> : null}{children}{footer ? <div style={{ marginTop: 4 }}>{footer}</div> : null}</Stack></Card>;
}
