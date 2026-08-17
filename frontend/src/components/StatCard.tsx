import { Card, Group, Stack, Text } from '@mantine/core';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { ReactNode } from 'react';
import { colors } from '../theme/tokens';

export function StatCard({ label, value, icon, color, trend }: { label: string; value: string | number; icon?: ReactNode; color?: string; trend?: { value: number; direction: 'up' | 'down' } }) {
  void color;
  const trendColor = trend?.direction === 'up' ? colors.success : colors.danger;
  const TrendIcon = trend?.direction === 'up' ? TrendingUp : TrendingDown;
  return (
    <Card className="erp-card" withBorder={false} padding="lg" radius="lg">
      <Group justify="space-between" align="flex-start"><Stack gap={5}><Text size="xs" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: '.08em' }}>{label}</Text><Text size="2rem" fw={700} lh={1.05}>{value}</Text>{trend ? <Group gap={4}><TrendIcon size={14} color={trendColor} /><Text size="xs" c={trendColor}>{trend.value}%</Text></Group> : null}</Stack>{icon ? <div style={{ width: 44, height: 44, display: 'grid', placeItems: 'center', borderRadius: 14, color: '#fff', background: 'linear-gradient(135deg,#0052FF,#4D7CFF)', boxShadow: '0 8px 18px rgba(0,82,255,.20)' }}>{icon}</div> : null}</Group>
    </Card>
  );
}
