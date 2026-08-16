import { Outlet, useLocation } from 'react-router-dom';
import { useSession } from '../auth/useSession';
import { rolesForPath } from './navConfig';
import { Forbidden } from '../../shell/Forbidden';

/**
 * Route-level role guard. Consumes the same `navConfig` map (via the current
 * pathname) as the sidebar, so hidden nav can never desync from route
 * protection (REQ-SHELL-03). Renders a full-page friendly `Forbidden` surface
 * when the role is not allowed.
 */
export function RequireRole() {
  const { user } = useSession();
  const location = useLocation();
  const required = rolesForPath(location.pathname);

  const allowed = !!user && required.some((role) => user.roles.includes(role));

  if (!allowed) {
    return <Forbidden />;
  }

  return <Outlet />;
}
