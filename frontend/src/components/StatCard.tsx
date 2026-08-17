import { Card, Group, Stack, Text } from '@mantine/core';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { ReactNode } from 'react';
import { colors } from '../theme/tokens';

/**
 * Compact stat card for dashboards.
 * Shows an icon, a dimmed label, a bold value, and an optional trend indicator.
 */
export function StatCard({
  label,
  value,
  icon,
  color,
  trend,
}: {
  label: string;
  value: string | number;
  icon?: ReactNode;
  color?: string;
  trend?: { value: number; direction: 'up' | 'down' };
}) {
  const trendColor = trend?.direction === 'up' ? colors.success : colors.danger;
  const TrendIcon = trend?.direction === 'up' ? TrendingUp : TrendingDown;

  return (
    <Card withBorder padding="md" radius="md">
      <Group justify="space-between" align="flex-start">
        <Stack gap={2}>
          <Text size="sm" c="dimmed">
            {label}
          </Text>
          <Text size="xl" fw={700}>
            {value}
          </Text>
          {trend ? (
            <Group gap={4}>
              <TrendIcon size={14} color={trendColor} />
              <Text size="xs" c={trendColor}>
                {trend.value}%
              </Text>
            </Group>
          ) : null}
        </Stack>
        {icon ? (
          <div style={{ color: color ?? colors.primary }}>{icon}</div>
        ) : null}
      </Group>
    </Card>
  );
}
