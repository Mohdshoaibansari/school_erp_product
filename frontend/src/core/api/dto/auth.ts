/**
 * Typed DTOs mirroring the C-03 authentication backend (kernel/auth/routes/auth.py).
 * IDs and timestamps are serialized as strings in JSON.
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse extends TokenResponse {
  is_platform_owner: boolean | null;
  user_tier: 'client_leadership' | 'institution' | null;
  client_id: string | null;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface ActivateRequest {
  invite_token: string;
  password: string;
}

export interface ActivateResponse {
  message: string;
  user_id: string;
  user_tier: string;
  client_slug: string;
}

export interface OtpRequest {
  email: string;
}

export interface OtpVerifyRequest {
  email: string;
  token: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirmRequest {
  token: string;
  new_password: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface MessageResponse {
  message: string;
}
