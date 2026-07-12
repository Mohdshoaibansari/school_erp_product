"""C-03 Authentication routes — FastAPI endpoints (D14, D19).

All 9 Phase 1 endpoints are mounted under /auth/.
Each endpoint delegates to AuthService for the actual logic.
Error responses follow D19 format (distinct status codes per failure mode).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.auth.dependencies import get_auth_service
from kernel.auth.services.service import AuthService, AuthError
from kernel.auth.utils.ip import get_client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================
# Request/Response DTOs
# ============================================================

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ActivateRequest(BaseModel):
    invite_token: str
    password: str


class OtpRequest(BaseModel):
    email: str


class OtpVerifyRequest(BaseModel):
    email: str
    token: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


# ============================================================
# Helper to convert AuthError → HTTPException (D19)
# ============================================================

def _raise_http_error(error: AuthError) -> None:
    """Convert AuthError to HTTPException with appropriate status code."""
    raise HTTPException(status_code=error.status_code, detail=str(error))


# ============================================================
# Auth endpoints (9.1 — 9.9)
# ============================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Email + password login → access + refresh tokens (9.1, D8, D8b, D18, D19)."""
    client_ip = get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent")
    try:
        result = await auth_service.login(
            ctx, request.email, request.password,
            ip_address=client_ip, user_agent=user_agent,
        )
        return TokenResponse(**result)
    except AuthError as e:
        _raise_http_error(e)


@router.post("/refresh", response_model=TokenResponse)
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


@router.post("/logout")
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


@router.post("/activate")
async def activate(
    request: ActivateRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Accept invite: verify JWT, set password, transition invited → active (9.4, D4, D29)."""
    try:
        result = await auth_service.activate(ctx, request.invite_token, request.password)
        return result
    except AuthError as e:
        _raise_http_error(e)


@router.post("/otp/request")
async def otp_request(
    request: OtpRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Request email OTP (9.5, D13)."""
    try:
        result = await auth_service.request_otp(ctx, request.email)
        return result
    except AuthError as e:
        _raise_http_error(e)


@router.post("/otp/verify", response_model=TokenResponse)
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


@router.post("/password/reset/request")
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


@router.post("/password/reset/confirm")
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


@router.post("/password/change")
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
