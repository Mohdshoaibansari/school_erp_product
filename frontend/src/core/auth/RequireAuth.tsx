import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Loader, Center } from '@mantine/core';
import { useSession } from './useSession';

/**
 * Route guard for protected routes. Redirects to /login (preserving the
 * intended destination in `state.from`) when there is no valid session.
 */
export function RequireAuth() {
  const { status } = useSession();
  const location = useLocation();

  if (status === 'loading') {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
