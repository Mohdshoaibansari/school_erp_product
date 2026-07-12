"""C-03 Authentication routes — FastAPI endpoints (D14).

These are the Phase 1 auth endpoints. All endpoints are mounted under /auth/.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from kernel.tenant_context import TenantContext, get_tenant_context

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
# Auth endpoints (Phase 2+ will implement the logic)
# ============================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> TokenResponse:
    """Email + password login → access + refresh tokens (D8, D8b)."""
    # Phase 2: implement AuthService.login()
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> TokenResponse:
    """Refresh access token using refresh token (D8b)."""
    # Phase 2: implement AuthService.refresh()
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    """Revoke refresh token (D17)."""
    # Phase 2: implement AuthService.logout()
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/activate")
async def activate(
    request: ActivateRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    """Accept invite: verify JWT, set password, transition invited → active (D4, D29)."""
    # Phase 2: implement AuthService.activate()
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/otp/request")
async def otp_request(
    request: OtpRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    """Request email OTP (D13)."""
    # Phase 2: implement AuthService.request_otp()
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/otp/verify", response_model=TokenResponse)
async def otp_verify(
    request: OtpVerifyRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> TokenResponse:
    """Verify OTP, return tokens (D13)."""
    # Phase 2: implement AuthService.verify_otp()
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/password/reset/request")
async def password_reset_request(
    request: PasswordResetRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    """Request password reset email (D15)."""
    # Phase 2: implement AuthService.request_password_reset()
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/password/reset/confirm")
async def password_reset_confirm(
    request: PasswordResetConfirmRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    """Confirm password reset with token (D15)."""
    # Phase 2: implement AuthService.confirm_password_reset()
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/password/change")
async def password_change(
    request: PasswordChangeRequest,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    """Change password (authenticated) (D16, D16b)."""
    # Phase 2: implement AuthService.change_password()
    raise HTTPException(status_code=501, detail="Not implemented yet")
