import { useContext } from 'react';
import { AuthContext, type AuthContextValue } from './AuthContext';

/**
 * Current session: user, roles, tenant ids, and auth actions.
 * Must be used within `<AuthProvider>`.
 */
export function useSession(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useSession must be used within AuthProvider');
  }
  return ctx;
}
