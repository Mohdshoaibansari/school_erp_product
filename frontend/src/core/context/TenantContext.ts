import { createContext } from 'react';

export interface TenantContextValue {
  clientId: string | null;
  institutionId: string | null;
  /** Institution Admin has a fixed context and no switcher. */
  isAdminFixed: boolean;
  setClientId: (id: string | null) => void;
  setInstitutionId: (id: string | null) => void;
}

export const TenantContext = createContext<TenantContextValue | null>(null);
