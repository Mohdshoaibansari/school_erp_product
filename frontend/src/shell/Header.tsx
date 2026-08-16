import { useEffect, useMemo } from 'react';
import {
  Avatar,
  Burger,
  Group,
  Menu,
  Select,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { platformApi } from '../core/api/platform';
import { institutionsApi } from '../core/api/institutions';
import { useSession } from '../core/auth/useSession';
import { useTenant } from '../core/context/useTenant';
import { resolveDefaultInstitution } from '../core/context/tenant';
import { ROLE_LABELS } from '../core/access/roles';

export function Header({ onMenuToggle }: { onMenuToggle: () => void }) {
  const { user, signOut } = useSession();
  const { clientId, institutionId, isAdminFixed, setClientId, setInstitutionId } =
    useTenant();
  const navigate = useNavigate();

  const isPlatformOwner = user?.isPlatformOwner ?? false;
  const isClientDirector = !!user?.roles.includes('client_director');

  const clientsQuery = useQuery({
    queryKey: ['platform', 'clients'],
    queryFn: () => platformApi.listClients().then((r) => r.data),
    enabled: isPlatformOwner,
  });

  const institutionsQuery = useQuery({
    queryKey: ['institutions', 'all'],
    queryFn: () => institutionsApi.listInstitutions(true).then((r) => r.data),
    enabled: isClientDirector,
  });

  // CD: default to last-used institution, falling back to the first (R4).
  useEffect(() => {
    if (isClientDirector && institutionsQuery.data?.length) {
      const resolved = resolveDefaultInstitution(
        institutionsQuery.data,
        institutionId,
      );
      if (resolved !== institutionId) {
        setInstitutionId(resolved);
      }
    }
  }, [
    isClientDirector,
    institutionsQuery.data,
    institutionId,
    setInstitutionId,
  ]);

  const clientOptions = useMemo(
    () =>
      (clientsQuery.data ?? []).map((c) => ({
        value: c.id,
        label: c.display_name,
      })),
    [clientsQuery.data],
  );

  const institutionOptions = useMemo(
    () =>
      (institutionsQuery.data ?? []).map((i) => ({
        value: i.id,
        label: i.display_name,
      })),
    [institutionsQuery.data],
  );

  const handleLogout = async () => {
    await signOut();
    navigate('/login', { replace: true });
  };

  const primaryRole = user?.roles[0] ?? null;

  return (
    <Group h="100%" px="md" justify="space-between" wrap="nowrap">
      <Group gap="sm" wrap="nowrap">
        <Burger
          opened={false}
          onClick={onMenuToggle}
          hiddenFrom="md"
          size="sm"
          aria-label="Toggle navigation"
        />
        <Text fw={700} size="lg">
          School ERP
        </Text>
      </Group>

      <Group gap="sm" wrap="nowrap">
        {!isAdminFixed && isPlatformOwner && (
          <Select
            data-testid="client-switcher"
            placeholder="Select client"
            data={clientOptions}
            value={clientId ?? null}
            onChange={(v) => setClientId(v)}
            w={200}
            searchable
            clearable={false}
          />
        )}
        {!isAdminFixed && isClientDirector && (
          <Select
            data-testid="institution-switcher"
            placeholder="Select institution"
            data={institutionOptions}
            value={institutionId ?? null}
            onChange={(v) => setInstitutionId(v)}
            w={200}
            searchable
            clearable={false}
          />
        )}

        <Menu position="bottom-end" withinPortal>
          <Menu.Target>
            <UnstyledButton>
              <Group gap="xs">
                <Avatar radius="xl" color="blue" size="sm">
                  {user?.email?.charAt(0).toUpperCase() ?? 'U'}
                </Avatar>
                <div className="hide-on-mobile">
                  <Text size="sm" fw={500} lh={1.2}>
                    {user?.email ?? 'User'}
                  </Text>
                  <Text size="xs" c="dimmed" lh={1.2}>
                    {primaryRole ? ROLE_LABELS[primaryRole] : ''}
                  </Text>
                </div>
              </Group>
            </UnstyledButton>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item onClick={() => navigate('/account/change-password')}>
              Change password
            </Menu.Item>
            <Menu.Item color="red" onClick={handleLogout}>
              Log out
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>
    </Group>
  );
}
