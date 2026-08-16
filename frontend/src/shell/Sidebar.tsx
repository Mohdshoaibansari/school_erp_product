import { NavLink, Stack } from '@mantine/core';
import { useLocation, useNavigate } from 'react-router-dom';
import { navItemsForRoles } from '../core/access/navConfig';
import { useSession } from '../core/auth/useSession';

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const items = navItemsForRoles(user?.roles ?? []);

  return (
    <Stack gap={4} p="sm">
      {items.map((item) => (
        <NavLink
          key={item.path}
          label={item.label}
          active={location.pathname.startsWith(item.path)}
          onClick={() => {
            navigate(item.path);
            onNavigate?.();
          }}
          variant="filled"
        />
      ))}
    </Stack>
  );
}
