import { useEffect, useMemo } from 'react';
import { Avatar, Burger, Group, Menu, Select, Text, UnstyledButton, Badge } from '@mantine/core';
import { ChevronDown, LogOut, KeyRound, Building2, Globe2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useLocation } from 'react-router-dom';
import { platformApi } from '../core/api/platform';
import { institutionsApi } from '../core/api/institutions';
import { useSession } from '../core/auth/useSession';
import { useTenant } from '../core/context/useTenant';
import { resolveDefaultInstitution } from '../core/context/tenant';
import { ROLE_LABELS } from '../core/access/roles';

const titleMap: Record<string, string> = {
  '/platform/clients': 'Clients', '/platform/institution-types': 'Institution types',
  '/platform/ownership-transfers': 'Ownership transfers', '/institutions': 'Institutions',
  '/users': 'Users', '/academic/years': 'Academic years', '/academic/subjects': 'Subjects',
  '/academic/subject-groups': 'Subject groups', '/config/keys': 'Configuration',
  '/config/audit': 'Configuration audit', '/fees/types': 'Fee types',
  '/fees/assignments': 'Fee assignments', '/fees/payments': 'Payments',
  '/homework': 'Homework', '/homework/grades': 'Grades',
};

export function Header({ onMenuToggle }: { onMenuToggle: () => void }) {
  const { user, signOut } = useSession();
  const { clientId, institutionId, isAdminFixed, setClientId, setInstitutionId } = useTenant();
  const navigate = useNavigate();
  const location = useLocation();
  const isPlatformOwner = user?.isPlatformOwner ?? false;
  const isClientDirector = !!user?.roles.includes('client_director');

  const clientsQuery = useQuery({ queryKey: ['platform', 'clients'], queryFn: () => platformApi.listClients().then((r) => r.data), enabled: isPlatformOwner });
  const institutionsQuery = useQuery({ queryKey: ['institutions', 'all'], queryFn: () => institutionsApi.listInstitutions(true).then((r) => r.data), enabled: isClientDirector });

  useEffect(() => {
    if (isClientDirector && institutionsQuery.data?.length) {
      const resolved = resolveDefaultInstitution(institutionsQuery.data, institutionId);
      if (resolved !== institutionId) setInstitutionId(resolved);
    }
  }, [isClientDirector, institutionsQuery.data, institutionId, setInstitutionId]);

  const clientOptions = useMemo(() => (clientsQuery.data ?? []).map((c) => ({ value: c.id, label: c.display_name })), [clientsQuery.data]);
  const institutionOptions = useMemo(() => (institutionsQuery.data ?? []).map((i) => ({ value: i.id, label: i.display_name })), [institutionsQuery.data]);
  const primaryRole = user?.roles[0] ?? null;
  const pageTitle = Object.entries(titleMap).find(([path]) => location.pathname.startsWith(path))?.[1] ?? 'Workspace';

  const handleLogout = async () => { await signOut(); navigate('/login', { replace: true }); };

  return (
    <Group h="100%" px={{ base: 'md', md: 'xl' }} justify="space-between" wrap="nowrap">
      <Group gap="md" wrap="nowrap" style={{ minWidth: 0 }}>
        <Burger opened={false} onClick={onMenuToggle} hiddenFrom="md" size="sm" aria-label="Toggle navigation" />
        <div style={{ minWidth: 0 }}>
          <Text size="xs" fw={700} c="dimmed" tt="uppercase" style={{ letterSpacing: '.12em', fontFamily: 'JetBrains Mono' }}>School ERP</Text>
          <Text fw={600} size="sm" truncate>{pageTitle}</Text>
        </div>
      </Group>

      <Group gap="sm" wrap="nowrap">
        {!isAdminFixed && isPlatformOwner && (
          <Select data-testid="client-switcher" leftSection={<Globe2 size={15} />} placeholder="Select client" data={clientOptions} value={clientId ?? null} onChange={setClientId} w={{ base: 150, md: 220 }} searchable clearable={false} />
        )}
        {!isAdminFixed && isClientDirector && (
          <Select data-testid="institution-switcher" leftSection={<Building2 size={15} />} placeholder="Select institution" data={institutionOptions} value={institutionId ?? null} onChange={setInstitutionId} w={{ base: 150, md: 220 }} searchable clearable={false} />
        )}
        <Badge visibleFrom="sm" variant="light" color="success" leftSection={<span style={{ width: 6, height: 6, borderRadius: 999, background: '#16A34A', display: 'inline-block' }} />}>Live</Badge>
        <Menu position="bottom-end" withinPortal shadow="lg">
          <Menu.Target>
            <UnstyledButton className="erp-user-trigger" aria-label="Open user menu">
              <Group gap="xs" wrap="nowrap">
                <Avatar radius="xl" color="blue" size={38}>{user?.email?.charAt(0).toUpperCase() ?? 'U'}</Avatar>
                <div className="hide-on-mobile" style={{ maxWidth: 170 }}>
                  <Text size="sm" fw={600} truncate>{user?.email ?? 'User'}</Text>
                  <Text size="xs" c="dimmed" truncate>{primaryRole ? ROLE_LABELS[primaryRole] : ''}</Text>
                </div>
                <ChevronDown size={15} color="#64748B" />
              </Group>
            </UnstyledButton>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Label>Account</Menu.Label>
            <Menu.Item leftSection={<KeyRound size={16} />} onClick={() => navigate('/account/change-password')}>Change password</Menu.Item>
            <Menu.Item color="red" leftSection={<LogOut size={16} />} onClick={handleLogout}>Log out</Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>
    </Group>
  );
}
