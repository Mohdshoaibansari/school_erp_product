import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { theme } from '../../theme';
import { DataTable } from '../DataTable';

interface Row {
  name: string;
}

function renderTable(responsive: 'scroll' | 'collapse' = 'scroll') {
  const columns = [
    { key: 'name', header: 'Name', render: (r: Row) => r.name, hideBelow: 768 },
  ];
  return render(
    <MantineProvider theme={theme}>
      <DataTable
        columns={columns}
        rows={[{ name: 'A' }]}
        getRowKey={(r) => r.name}
        responsive={responsive}
      />
    </MantineProvider>,
  );
}

describe('DataTable (REQ-SHELL-12)', () => {
  it('applies the horizontal-scroll strategy by default', () => {
    const { container } = renderTable('scroll');
    expect(container.querySelector('[data-responsive="scroll"]')).toBeInTheDocument();
  });

  it('applies the collapse strategy and marks hide-below columns', () => {
    const { container } = renderTable('collapse');
    expect(container.querySelector('[data-responsive="collapse"]')).toBeInTheDocument();
    expect(container.querySelector('[data-col-hide-below="768"]')).toBeInTheDocument();
  });
});
