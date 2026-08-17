import { Group, Skeleton as MSkeleton, Stack, Table } from '@mantine/core';

/**
 * Animated skeleton placeholder that matches the DataTable shape.
 * Use while data is loading instead of a full-page spinner.
 */
export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <Table striped verticalSpacing="xs">
      <Table.Thead>
        <Table.Tr>
          {Array.from({ length: columns }).map((_, i) => (
            <Table.Th key={i}>
              <MSkeleton height={14} width={80} radius="sm" />
            </Table.Th>
          ))}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {Array.from({ length: rows }).map((_, r) => (
          <Table.Tr key={r}>
            {Array.from({ length: columns }).map((_, c) => (
              <Table.Td key={c}>
                <MSkeleton
                  height={14}
                  width={c === 0 ? 120 : 80}
                  radius="sm"
                />
              </Table.Td>
            ))}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

/**
 * Animated skeleton placeholder that matches a Card shape.
 */
export function CardSkeleton() {
  return (
    <Stack gap="sm" p="md">
      <Group justify="space-between">
        <MSkeleton height={20} width="40%" radius="sm" />
        <MSkeleton height={20} width={60} radius="sm" />
      </Group>
      <MSkeleton height={14} width="80%" radius="sm" />
      <MSkeleton height={14} width="60%" radius="sm" />
    </Stack>
  );
}
