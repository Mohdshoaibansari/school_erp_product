import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useSession } from '../auth/useSession';
import { TenantContext, type TenantContextValue } from './TenantContext';
import {
  loadLastUsedInstitution,
  persistLastUsedInstitution,
} from './tenant';

export function TenantProvider({ children }: { children: ReactNode }) {
  const { user } = useSession();
  const isAdminFixed = !!user && user.roles.includes('institution_admin');

  const [clientId, setClientIdState] = useState<string | null>(
    user?.clientId ?? null,
  );
  const [institutionId, setInstitutionIdState] = useState<string | null>(() => {
    if (isAdminFixed) return user?.institutionId ?? null;
    return loadLastUsedInstitution() ?? user?.institutionId ?? null;
  });

  // Re-sync when the signed-in user changes (login/logout/refresh of identity).
  useEffect(() => {
    setClientIdState(user?.clientId ?? null);
    if (isAdminFixed) {
      setInstitutionIdState(user?.institutionId ?? null);
    } else {
      setInstitutionIdState(
        loadLastUsedInstitution() ?? user?.institutionId ?? null,
      );
    }
  }, [user, isAdminFixed]);

  const setClientId = useCallback((id: string | null) => {
    setClientIdState(id);
  }, []);

  const setInstitutionId = useCallback((id: string | null) => {
    persistLastUsedInstitution(id);
    setInstitutionIdState(id);
  }, []);

  const value = useMemo<TenantContextValue>(
    () => ({
      clientId,
      institutionId,
      isAdminFixed,
      setClientId,
      setInstitutionId,
    }),
    [clientId, institutionId, isAdminFixed, setClientId, setInstitutionId],
  );

  return (
    <TenantContext.Provider value={value}>{children}</TenantContext.Provider>
  );
}
