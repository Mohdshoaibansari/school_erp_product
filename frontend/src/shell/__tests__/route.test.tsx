import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../../test/testUtils';
import App from '../../App';

describe('route table (REQ-SHELL-06, REQ-FE-USR-06)', () => {
  it('renders NotFound for an unknown route', async () => {
    renderWithProviders(<App />, { route: '/does-not-exist', claims: null });
    expect(await screen.findByText('Page not found')).toBeInTheDocument();
  });

  it('has no Roles & Permissions route', async () => {
    renderWithProviders(<App />, { route: '/roles', claims: null });
    expect(await screen.findByText('Page not found')).toBeInTheDocument();
  });

  it('has no permissions management route', async () => {
    renderWithProviders(<App />, { route: '/permissions', claims: null });
    expect(await screen.findByText('Page not found')).toBeInTheDocument();
  });
});
