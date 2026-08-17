import { Box, Menu, ActionIcon, ScrollArea, Table, Text, Stack, Group, Pagination, Center } from '@mantine/core';
import { Inbox, MoreVertical } from 'lucide-react';
import type { ReactNode } from 'react';

export interface DataTableColumn<T> { key: string; header: ReactNode; render: (row: T) => ReactNode; hideBelow?: number; }
export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]; rows: T[]; getRowKey: (row: T) => string;
  responsive?: 'scroll' | 'collapse'; emptyMessage?: string; actions?: (row: T) => ReactNode;
  pagination?: { page: number; pageSize: number; total: number; onPageChange: (page: number) => void };
}

export function DataTable<T>({ columns, rows, getRowKey, responsive = 'scroll', emptyMessage, actions, pagination }: DataTableProps<T>) {
  const colProps = (col: DataTableColumn<T>) => responsive === 'collapse' && col.hideBelow !== undefined ? { 'data-col-hide-below': col.hideBelow } : {};
  const allColumns = actions ? [...columns, { key: '__actions', header: '', render: () => null as unknown as ReactNode }] : columns;
  const totalColSpan = allColumns.length;
  const table = (
    <Table verticalSpacing="md" horizontalSpacing="lg">
      <Table.Thead><Table.Tr>{columns.map((col) => <Table.Th key={col.key} {...colProps(col)}>{col.header}</Table.Th>)}{actions ? <Table.Th key="__actions" /> : null}</Table.Tr></Table.Thead>
      <Table.Tbody>
        {rows.length === 0 ? (
          <Table.Tr><Table.Td colSpan={totalColSpan}><Center py={56}><Stack align="center" gap={6}><Center style={{ width: 48, height: 48, borderRadius: 14, background: '#F1F5F9', color: '#64748B' }}><Inbox size={22} /></Center><Text fw={600} size="sm">No records yet</Text><Text c="dimmed" size="sm">{emptyMessage ?? 'There is nothing to display yet.'}</Text></Stack></Center></Table.Td></Table.Tr>
        ) : rows.map((row) => (
          <Table.Tr key={getRowKey(row)}>{columns.map((col) => <Table.Td key={col.key} {...colProps(col)}>{col.render(row)}</Table.Td>)}{actions ? <Table.Td key="__actions"><Menu shadow="lg" withinPortal position="bottom-end"><Menu.Target><ActionIcon variant="subtle" size="sm" aria-label="Row actions"><MoreVertical size={16} /></ActionIcon></Menu.Target><Menu.Dropdown>{actions(row)}</Menu.Dropdown></Menu></Table.Td> : null}</Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
  const content = responsive === 'scroll' ? <ScrollArea type="hover">{table}</ScrollArea> : <div data-responsive="collapse">{table}</div>;
  if (!pagination) return <Box className="erp-card" style={{ overflow: 'hidden' }}>{content}</Box>;
  const start = pagination.total ? (pagination.page - 1) * pagination.pageSize + 1 : 0;
  const end = Math.min(pagination.page * pagination.pageSize, pagination.total);
  const totalPages = Math.max(1, Math.ceil(pagination.total / pagination.pageSize));
  return <Box><Box className="erp-card" style={{ overflow: 'hidden' }}>{content}</Box><Group justify="space-between" mt="md"><Text size="xs" c="dimmed">Showing {start}&ndash;{end} of {pagination.total}</Text><Pagination value={pagination.page} total={totalPages} onChange={pagination.onPageChange} size="sm" /></Group></Box>;
}
