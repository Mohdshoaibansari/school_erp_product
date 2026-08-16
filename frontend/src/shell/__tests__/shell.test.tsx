import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/server';
import { renderWithProviders } from '../../test/testUtils';
import type { JwtClaims } from '../../core/auth/session';
import { Sidebar } from '../Sidebar';
import { Header } from '../Header';
import { Forbidden } from '../Forbidden';
import { ApiError } from '../../core/api/errors';

const poClaims: JwtClaims & { sub: string } = {
  sub: 'po1',
  email: 'po@school.test',
  roles: ['platform_owner'],
  is_platform_owner: true,
  client_id: null,
  institution_id: null,
};

const cdClaims: JwtClaims & { sub: string } = {
  sub: 'cd1',
  email: 'cd@school.test',
  roles: ['client_director'],
  user_tier: 'client_leadership',
  client_id: 'c1',
  institution_id: null,
};

const adminClaims: JwtClaims & { sub: string } = {
  sub: 'a1',
  email: 'admin@school.test',
  roles: ['institution_admin'],
  user_tier: 'institution',
  client_id: 'c1',
  institution_id: 'i1',
};

describe('Sidebar role filtering (REQ-SHELL-03)', () => {
  it('shows only platform-owner modules for Platform Owner', () => {
    renderWithProviders(<Sidebar />, { claims: poClaims });
    expect(screen.getByText('Clients')).toBeInTheDocument();
    expect(screen.queryByText('Users')).not.toBeInTheDocument();
    expect(screen.queryByText('Institutions')).not.toBeInTheDocument();
  });

  it('shows institutions + users for Client Director', () => {
    renderWithProviders(<Sidebar />, { claims: cdClaims });
    expect(screen.getByText('Institutions')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.queryByText('Clients')).not.toBeInTheDocument();
  });

  it('shows only users for Institution Admin', () => {
    renderWithProviders(<Sidebar />, { claims: adminClaims });
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.queryByText('Clients')).not.toBeInTheDocument();
    expect(screen.queryByText('Institutions')).not.toBeInTheDocument();
  });
});

describe('Header context switcher (REQ-SHELL-05)', () => {
  it('renders a client switcher for Platform Owner', async () => {
    server.use(
      http.get('/api/v1/platform/clients', () => HttpResponse.json([])),
    );
    renderWithProviders(<Header onMenuToggle={() => {}} />, { claims: poClaims });
    expect(await screen.findByTestId('client-switcher')).toBeInTheDocument();
    expect(screen.queryByTestId('institution-switcher')).not.toBeInTheDocument();
  });

  it('renders an institution switcher for Client Director', async () => {
    server.use(
      http.get('/api/v1/institutions', () => HttpResponse.json([])),
    );
    renderWithProviders(<Header onMenuToggle={() => {}} />, { claims: cdClaims });
    expect(await screen.findByTestId('institution-switcher')).toBeInTheDocument();
    expect(screen.queryByTestId('client-switcher')).not.toBeInTheDocument();
  });

  it('renders no switcher for Institution Admin', async () => {
    renderWithProviders(<Header onMenuToggle={() => {}} />, { claims: adminClaims });
    expect(screen.queryByTestId('client-switcher')).not.toBeInTheDocument();
    expect(screen.queryByTestId('institution-switcher')).not.toBeInTheDocument();
  });
});

describe('Forbidden (REQ-SHELL-07)', () => {
  it('renders a friendly message, never a raw error', () => {
    renderWithProviders(<Forbidden error={new ApiError(403, 'Platform Owner privileges required')} />, {
      claims: adminClaims,
    });
    expect(screen.getByText('You don\'t have permission')).toBeInTheDocument();
    expect(screen.queryByText(/stack trace|at Object/i)).not.toBeInTheDocument();
  });
});
