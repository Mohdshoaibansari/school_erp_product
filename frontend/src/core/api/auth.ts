import { api } from './client';
import type {
  ActivateRequest,
  ActivateResponse,
  LoginRequest,
  LoginResponse,
  LogoutRequest,
  MessageResponse,
  OtpRequest,
  OtpVerifyRequest,
  PasswordChangeRequest,
  PasswordResetConfirmRequest,
  PasswordResetRequest,
  RefreshRequest,
  TokenResponse,
} from './dto/auth';

export const authApi = {
  login: (payload: LoginRequest) =>
    api.post<LoginResponse>('/api/auth/login', payload),

  refresh: (payload: RefreshRequest) =>
    api.post<TokenResponse>('/api/auth/refresh', payload),

  logout: (payload: LogoutRequest) =>
    api.post<MessageResponse>('/api/auth/logout', payload),

  activate: (payload: ActivateRequest) =>
    api.post<ActivateResponse>('/api/auth/activate', payload),

  requestOtp: (payload: OtpRequest) =>
    api.post<MessageResponse>('/api/auth/otp/request', payload),

  verifyOtp: (payload: OtpVerifyRequest) =>
    api.post<TokenResponse>('/api/auth/otp/verify', payload),

  requestPasswordReset: (payload: PasswordResetRequest) =>
    api.post<MessageResponse>('/api/auth/password/reset/request', payload),

  confirmPasswordReset: (payload: PasswordResetConfirmRequest) =>
    api.post<MessageResponse>('/api/auth/password/reset/confirm', payload),

  changePassword: (payload: PasswordChangeRequest) =>
    api.post<MessageResponse>('/api/auth/password/change', payload),
};
