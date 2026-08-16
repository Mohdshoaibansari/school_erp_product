import { useContext } from 'react';
import { TenantContext, type TenantContextValue } from './TenantContext';

export function useTenant(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) {
    throw new Error('useTenant must be used within TenantProvider');
  }
  return ctx;
}
