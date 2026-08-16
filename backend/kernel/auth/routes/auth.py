"""C-03 Authentication routes — FastAPI endpoints (D14, D19).

All 9 Phase 1 endpoints are mounted under /auth/.
Each endpoint delegates to AuthService for the actual logic.
Error responses follow D19 format (distinct status codes per failure mode).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.auth.dependencies import get_auth_service
from kernel.auth.services.service import AuthService, AuthError
from kernel.auth.utils.ip import get_client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================
# Request/Response DTOs
# ============================================================

class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type (always bearer)")
    expires_in: int = Field(3600, description="Access token lifetime in seconds")


class LoginResponse(BaseModel):
    """Unified login response with optional tier fields (D9)."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type (always bearer)")
    expires_in: int = Field(3600, description="Access token lifetime in seconds")
    is_platform_owner: bool | None = Field(None, description="True if the user is a platform owner")
    user_tier: str | None = Field(None, description="User tier (client_leadership or institution)")
    client_id: str | None = Field(None, description="Client ID when login is client-scoped")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="JWT refresh token")


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., description="JWT refresh token to revoke")


class ActivateRequest(BaseModel):
    invite_token: str = Field(..., description="Invite JWT from the activation link")
    password: str = Field(..., description="New password to set on activation")


class ActivateResponse(BaseModel):
    """Response DTO for activate endpoint (D4)."""
    message: str = Field(..., description="Success message")
    user_id: str = Field(..., description="Activated user's ID")
    user_tier: str = Field(..., description="User tier (client_leadership or institution)")
    client_slug: str = Field(..., description="Client slug for login redirect")


class OtpRequest(BaseModel):
    email: str = Field(..., description="Email to send the OTP to")


class OtpVerifyRequest(BaseModel):
    email: str = Field(..., description="Email that requested the OTP")
    token: str = Field(..., description="OTP code to verify")


class PasswordResetRequest(BaseModel):
    email: str = Field(..., description="Email to send the password reset link to")


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., description="Password reset token from the email link")
    new_password: str = Field(..., description="New password to set")


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password to set")


# ============================================================
# Helper to convert AuthError → HTTPException (D19)
# ============================================================

def _raise_http_error(error: AuthError) -> None:
    """Convert AuthError to HTTPException with appropriate status code."""
    raise HTTPException(status_code=error.status_code, detail=str(error))


# ============================================================
# Auth endpoints (9.1 — 9.9)
# ============================================================

@router.post("/login", response_model=LoginResponse, summary="Login")
async def login(
    request: LoginRequest,
    http_request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Email + password login → access + refresh tokens (9.1, D8, D8b, D18, D19)."""
    client_ip = get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent")
    try:
        result = await auth_service.login(
            ctx, request.email, request.password,
            ip_address=client_ip, user_agent=user_agent,
        )
        return LoginResponse(**result)
    except AuthError as e:
        _raise_http_error(e)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh token")
async def refresh(
    request: RefreshRequest,
    http_request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh access token using refresh token (9.2, D8b)."""
    client_ip = get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent")
    try:
        result = await auth_service.refresh(
            ctx, request.refresh_token,
            ip_address=client_ip, user_agent=user_agent,
        )
        return TokenResponse(**result)
    except AuthError as e:
        _raise_http_error(e)


@router.post("/logout", summary="Logout")
async def logout(
    request: LogoutRequest,
    http_request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Revoke refresh token (9.3, D17)."""
    client_ip = get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent")
    try:
        await auth_service.logout(
            ctx, request.refresh_token,
            ip_address=client_ip, user_agent=user_agent,
        )
        return {"message": "Logged out successfully"}
    except AuthError as e:
        _raise_http_error(e)


@router.post("/activate", response_model=ActivateResponse, summary="Activate user")
async def activate(
    request: ActivateRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> ActivateResponse:
    """Accept invite: verify JWT, set password, transition invited → active (9.4, D4, D29).

    Returns user_tier and client_slug for frontend redirect to tenant-scoped login."""
    try:
        result = await auth_service.activate(ctx, request.invite_token, request.password)
        return result
    except AuthError as e:
        _raise_http_error(e)


@router.post("/otp/request", summary="Request OTP")
async def otp_request(
    request: OtpRequest,
    http_request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Request email OTP (9.5, D13)."""
    client_ip = get_client_ip(http_request)
    try:
        result = await auth_service.request_otp(ctx, request.email, ip_address=client_ip)
        return result
    except AuthError as e:
        _raise_http_error(e)


@router.post("/otp/verify", response_model=TokenResponse, summary="Verify OTP")
async def otp_verify(
    request: OtpVerifyRequest,
    http_request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Verify OTP, return tokens (9.6, D13)."""
    client_ip = get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent")
    try:
        result = await auth_service.verify_otp(
            ctx, request.email, request.token,
            ip_address=client_ip, user_agent=user_agent,
        )
        return TokenResponse(**result)
    except AuthError as e:
        _raise_http_error(e)


@router.post("/password/reset/request", summary="Request password reset")
async def password_reset_request(
    request: PasswordResetRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Request password reset email (9.7, D15)."""
    try:
        result = await auth_service.request_password_reset(ctx, request.email)
        return result
    except AuthError as e:
        _raise_http_error(e)


@router.post("/password/reset/confirm", summary="Confirm password reset")
async def password_reset_confirm(
    request: PasswordResetConfirmRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Confirm password reset with token (9.8, D15)."""
    try:
        result = await auth_service.confirm_password_reset(
            ctx, request.token, request.new_password,
        )
        return result
    except AuthError as e:
        _raise_http_error(e)


@router.post("/password/change", summary="Change password")
async def password_change(
    request: PasswordChangeRequest,
    http_request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Change password (authenticated) (9.9, D16, D16b)."""
    client_ip = get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent")
    try:
        result = await auth_service.change_password(
            ctx, request.current_password, request.new_password,
            ip_address=client_ip, user_agent=user_agent,
        )
        return result
    except AuthError as e:
        _raise_http_error(e)
