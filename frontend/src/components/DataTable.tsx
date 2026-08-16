import { ScrollArea, Table, Text } from '@mantine/core';
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
}: DataTableProps<T>) {
  const colProps = (col: DataTableColumn<T>) =>
    responsive === 'collapse' && col.hideBelow !== undefined
      ? { 'data-col-hide-below': col.hideBelow }
      : {};

  const table = (
    <Table striped verticalSpacing="xs">
      <Table.Thead>
        <Table.Tr>
          {columns.map((col) => (
            <Table.Th key={col.key} {...colProps(col)}>
              {col.header}
            </Table.Th>
          ))}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {rows.length === 0 ? (
          <Table.Tr>
            <Table.Td colSpan={columns.length}>
              <Text c="dimmed" ta="center" py="md">
                No records
              </Text>
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
            </Table.Tr>
          ))
        )}
      </Table.Tbody>
    </Table>
  );

  if (responsive === 'scroll') {
    return (
      <ScrollArea data-responsive="scroll" type="hover">
        {table}
      </ScrollArea>
    );
  }

  return <div data-responsive="collapse">{table}</div>;
}
