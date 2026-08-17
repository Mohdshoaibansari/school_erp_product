import { Navigate } from 'react-router-dom';
import { Center, Loader, Text } from '@mantine/core';
import { useSession } from '../core/auth/useSession';
import { navItemsForRoles } from '../core/access/navConfig';

/**
 * Root route ("/"): send unauthenticated users to /login and authenticated
 * users to their first role-allowed module. Avoids the catch-all NotFound and
 * the PublicOnly → "/" redirect loop.
 */
export function HomeRedirect() {
  const { status, user } = useSession();

  if (status === 'loading') {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace />;
  }

  const first = navItemsForRoles(user?.roles ?? [])[0];
  if (!first) {
    return (
      <Center h="100vh">
        <Text c="dimmed">No access — your account has no assigned roles.</Text>
      </Center>
    );
  }

  return <Navigate to={first.path} replace />;
}
