import { createContext } from 'react';
import type { LoginResponse } from '../api/dto/auth';
import type { SessionUser } from './session';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface AuthContextValue {
  user: SessionUser | null;
  status: AuthStatus;
  signIn: (response: LoginResponse) => void;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
