import { useSession } from '../auth/useSession';
import { hasRole, type Role } from './roles';

export interface Permissions {
  roles: Role[];
  can: (role: Role) => boolean;
  canAny: (roles: Role[]) => boolean;
}

/** Derived from the JWT `roles` claim (management roles only). */
export function usePermissions(): Permissions {
  const { user } = useSession();
  const roles = user?.roles ?? [];

  return {
    roles,
    can: (role: Role) => hasRole(roles, role),
    canAny: (required: Role[]) =>
      required.some((role) => hasRole(roles, role)),
  };
}
