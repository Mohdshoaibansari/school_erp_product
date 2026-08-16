import { Navigate, Outlet } from 'react-router-dom';
import { useSession } from './useSession';

/** Redirects already-authenticated users away from public auth screens. */
export function PublicOnly() {
  const { status } = useSession();

  if (status === 'authenticated') {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
