import { Badge } from '@mantine/core';

type PillColor = 'success' | 'warning' | 'danger' | 'blue' | 'gray';

const STATUS_COLORS: Record<string, PillColor> = {
  active: 'success',
  planning: 'blue',
  onboarding: 'warning',
  pending: 'warning',
  invited: 'blue',
  suspended: 'warning',
  archived: 'gray',
  inactive: 'gray',
  closed: 'gray',
  rejected: 'danger',
  approved: 'success',
};

function colorFor(status: string): PillColor {
  return STATUS_COLORS[status.toLowerCase()] ?? 'blue';
}

function labelFor(status: string): string {
  return status
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function StatusPill({ status }: { status: string }) {
  return (
    <Badge color={colorFor(status)} variant="light" radius="sm">
      {labelFor(status)}
    </Badge>
  );
}
