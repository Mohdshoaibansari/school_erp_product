import { Card, Text } from '@mantine/core';
import type { ReactNode } from 'react';

/** Themed card wrapper for forms. */
export function FormCard({
  title,
  children,
  footer,
}: {
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <Card withBorder padding="lg">
      {title ? (
        <Text fw={600} mb="md">
          {title}
        </Text>
      ) : null}
      {children}
      {footer ? <div style={{ marginTop: 16 }}>{footer}</div> : null}
    </Card>
  );
}
