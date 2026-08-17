import { Box, Menu, ActionIcon, ScrollArea, Table, Text, Stack, Group, Pagination, Center } from '@mantine/core';
import { Inbox, MoreVertical } from 'lucide-react';
import type { ReactNode } from 'react';

export interface DataTableColumn<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  /** Hide this column below the given viewport width (px) when `responsive === 'collapse'`. */
  hideBelow?: number;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  /** 'scroll' wraps in a horizontal ScrollArea; 'collapse' hides `hideBelow` columns on narrow screens. */
  responsive?: 'scroll' | 'collapse';
  /** Custom message shown when rows is empty. Defaults to "No records". */
  emptyMessage?: string;
  /** Row actions rendered as a three-dot menu appended as the last column. */
  actions?: (row: T) => ReactNode;
  /** Pagination controls rendered below the table. */
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
}

/**
 * Themed data table (REQ-SHELL-12). Two responsive strategies:
 * - scroll: horizontal scroll on narrow viewports (default)
 * - collapse: hide columns below their `hideBelow` breakpoint via CSS
 */
export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  responsive = 'scroll',
  emptyMessage,
  actions,
  pagination,
}: DataTableProps<T>) {
  const colProps = (col: DataTableColumn<T>) =>
    responsive === 'collapse' && col.hideBelow !== undefined
      ? { 'data-col-hide-below': col.hideBelow }
      : {};

  const allColumns = actions
    ? [...columns, { key: '__actions', header: '', render: () => null as unknown as ReactNode }]
    : columns;

  const totalColSpan = allColumns.length;

  const table = (
    <Table striped verticalSpacing="xs">
      <Table.Thead>
        <Table.Tr>
          {columns.map((col) => (
            <Table.Th key={col.key} {...colProps(col)}>
              {col.header}
            </Table.Th>
          ))}
          {actions ? <Table.Th key="__actions" /> : null}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {rows.length === 0 ? (
          <Table.Tr>
            <Table.Td colSpan={totalColSpan}>
              <Center py="xl">
                <Stack align="center" gap="xs">
                  <Inbox size={40} color="var(--mantine-color-dimmed)" />
                  <Text fw={600} size="sm">
                    No records
                  </Text>
                  <Text c="dimmed" size="sm">
                    {emptyMessage ?? 'There is nothing to display yet.'}
                  </Text>
                </Stack>
              </Center>
            </Table.Td>
          </Table.Tr>
        ) : (
          rows.map((row) => (
            <Table.Tr key={getRowKey(row)}>
              {columns.map((col) => (
                <Table.Td key={col.key} {...colProps(col)}>
                  {col.render(row)}
                </Table.Td>
              ))}
              {actions ? (
                <Table.Td key="__actions">
                  <Menu shadow="md" withinPortal position="bottom-end" zIndex={300}>
                    <Menu.Target>
                      <ActionIcon variant="subtle" size="sm" aria-label="Row actions">
                        <MoreVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>{actions(row)}</Menu.Dropdown>
                  </Menu>
                </Table.Td>
              ) : null}
            </Table.Tr>
          ))
        )}
      </Table.Tbody>
    </Table>
  );

  const tableContent =
    responsive === 'scroll' ? (
      <ScrollArea data-responsive="scroll" type="hover">
        {table}
      </ScrollArea>
    ) : (
      <div data-responsive="collapse">{table}</div>
    );

  if (!pagination) {
    return tableContent;
  }

  const start = (pagination.page - 1) * pagination.pageSize + 1;
  const end = Math.min(pagination.page * pagination.pageSize, pagination.total);
  const totalPages = Math.max(1, Math.ceil(pagination.total / pagination.pageSize));

  return (
    <Box>
      {tableContent}
      <Group justify="space-between" mt="md">
        <Text size="sm" c="dimmed">
          Showing {start}&ndash;{end} of {pagination.total}
        </Text>
        <Pagination
          value={pagination.page}
          total={totalPages}
          onChange={pagination.onPageChange}
          size="sm"
        />
      </Group>
    </Box>
  );
}
