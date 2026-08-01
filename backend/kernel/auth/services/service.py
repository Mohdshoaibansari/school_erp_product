"""AuthService — C-03 Authentication service (D8, D8b, D13, D15, D16, D16b, D17, D18, D19, D25, D28a, D33).

Orchestrates SupabaseAuthClient + app_user repo + login_attempt repo + invite token + TenantContext.
All auth endpoints delegate to this service.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

from kernel.tenant_context import TenantContext
from kernel.user.repos.user_repo import UserRepository
from kernel.auth.repos.login_attempt_repo import LoginAttemptRepository
from kernel.auth.supabase_client import SupabaseAuthClient, SupabaseAuthError
from kernel.auth.services.invite_token import (
    InvalidInviteTokenError,
    mint_invite_token,
    verify_invite_token,
)
from kernel.auth.services.dtos import LoginAttemptDTO, TokenResponseDTO
from kernel.audit import AuditEmitter, DefaultAuditEmitter


class AuthError(Exception):
    """Base exception for auth service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthService:
    """Published service interface for C-03 (A4).

    Endpoints call this; it orchestrates auth flows.
    """

    def __init__(
        self,
        supabase_client: SupabaseAuthClient,
        session_factory: sessionmaker[Session],
        audit_emitter: AuditEmitter | None = None,
        user_repo: UserRepository | None = None,
        login_attempt_repo: LoginAttemptRepository | None = None,
    ) -> None:
        self._supabase = supabase_client
        self._session_factory = session_factory
        self._audit = audit_emitter or DefaultAuditEmitter()
        self._user_repo = user_repo or UserRepository(audit_emitter=self._audit)
        self._login_attempt_repo = login_attempt_repo or LoginAttemptRepository()

    async def login(
        self,
        ctx: TenantContext,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Email + password login (D8, D8b, D18, D19, D33).

        Calls Supabase sign_in_with_password, looks up app_user by UUID (sub),
        checks lifecycle is active (D18), checks app_user.client_id == ctx.client_id (cross-tenant),
        records login_success/login_failure, returns tokens or raises AuthError.
        """
        logger.info("[AUTH] Login attempt: email=%s client_id=%s ip=%s", email, ctx.client_id, ip_address)
        try:
            result = await self._supabase.sign_in_with_password(email, password)
            logger.info("[AUTH] Supabase login success: email=%s", email)
        except SupabaseAuthError as e:
            # Supabase auth failed — record failure and look up user by email (D33)
            logger.warning("[AUTH] Login failed: email=%s error=%s", email, str(e)[:100])
            self._record_login_attempt(
                ctx, email, "login_failure",
                ip_address=ip_address, user_agent=user_agent,
            )
            raise AuthError("Invalid email or password", status_code=401) from e

        # Supabase auth succeeded — check for platform owner first (D2)
        supabase_user = result.get("user", {})
        user_id_str = supabase_user.get("id")
        if not user_id_str:
            logger.warning("[AUTH] Login failed: no user_id in Supabase response for email=%s", email)
            self._record_login_attempt(
                ctx, email, "login_failure",
                ip_address=ip_address, user_agent=user_agent,
            )
            raise AuthError("User record missing. Contact administrator.", status_code=403)

        user_id = uuid.UUID(user_id_str)
        user_metadata = supabase_user.get("user_metadata") or {}
        is_platform_owner = user_metadata.get("is_platform_owner", False)

        logger.info("[AUTH] Supabase user found: user_id=%s email=%s is_platform_owner=%s",
                     user_id, email, is_platform_owner)

        # Platform owner — skip app_user lookup (D2, D16, D26)
        if is_platform_owner:
            # Don't record login_attempt for platform owner — they have no
            # app_user row, and login_attempt.user_id has FK to app_user.
            logger.info("[AUTH] Platform owner login success: user_id=%s email=%s", user_id, email)

            # D3: Mint our own JWT with is_platform_owner claim.
            # Supabase's JWT doesn't carry this claim, so we issue our own.
            from jose import jwt
            jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "test-secret-for-c01")
            now = datetime.now(timezone.utc)
            from kernel.config.resolver import config
            jwt_expiry = int(config.get('auth.jwtExpirySeconds') or 3600)

            platform_jwt = jwt.encode({
                "sub": str(user_id),
                "is_platform_owner": True,
                "iat": now,
                "exp": now + timedelta(seconds=jwt_expiry),
            }, jwt_secret, algorithm="HS256")

            return {
                "access_token": platform_jwt,
                "refresh_token": "",  # Platform owner doesn't use refresh
                "token_type": "bearer",
                "expires_in": jwt_expiry,
                "is_platform_owner": True,
            }

        # Client-leadership user (D2) — look up client_user instead of app_user
        user_tier = user_metadata.get("user_tier")
        if user_tier == "client_leadership":
            return await self._login_client_leadership(
                ctx, user_id, email,
                ip_address=ip_address, user_agent=user_agent,
            )

        # Institution user — fall through to existing app_user lookup
        if user_tier != "institution":
            # D14: strict-fail for users without user_tier flag
            logger.warning("[AUTH] Login failed: no user_tier flag for user_id=%s email=%s metadata=%s",
                           user_id, email, user_metadata)
            raise AuthError("Account requires reconfiguration. Contact administrator.", status_code=403)

        # Normal user — look up app_user by UUID
        with self._session_factory() as session:
            # Look up app_user by UUID — bypass tenant filter since login
            # happens before the client context is fully resolved (D25)
            from kernel.user.models.user import User
            user_obj = session.get(User, user_id)
            user_dto = self._user_repo._to_dto(user_obj) if user_obj else None
            if not user_dto:
                # Supabase user exists but no app_user row (D19 failure 2)
                logger.warning("[AUTH] Login failed: no app_user found for user_id=%s", user_id)
                self._record_login_attempt(
                    ctx, email, "login_failure",
                    ip_address=ip_address, user_agent=user_agent,
                )
                raise AuthError("User record missing. Contact administrator.", status_code=403)

            # Check lifecycle is active (D18)
            if user_dto.lifecycle_status != "active":
                logger.warning("[AUTH] Login failed: user_id=%s lifecycle=%s", user_id, user_dto.lifecycle_status)
                self._record_login_attempt(
                    ctx, email, "login_failure",
                    user_id=user_id, ip_address=ip_address, user_agent=user_agent,
                )
                raise AuthError(
                    f"Account is not active. Status: {user_dto.lifecycle_status}. Contact administrator.",
                    status_code=403,
                )

            # Check cross-tenant (D19 failure 3)
            # Platform owners can log in from any subdomain
            if ctx.client_id and user_dto.client_id != ctx.client_id and "platform_owner" not in (ctx.roles or []):
                logger.warning("[AUTH] Cross-tenant login blocked: user_id=%s user_client=%s ctx_client=%s",
                               user_id, user_dto.client_id, ctx.client_id)
                self._record_login_attempt(
                    ctx, email, "login_failure",
                    user_id=user_id, ip_address=ip_address, user_agent=user_agent,
                )
                raise AuthError("Access denied. Account does not belong to this client.", status_code=403)

            # Login succeeded — record success
            self._record_login_attempt(
                ctx, email, "login_success",
                user_id=user_id, ip_address=ip_address, user_agent=user_agent,
            )

            from kernel.config.resolver import config
            jwt_expiry = int(config.get('auth.jwtExpirySeconds') or 3600)

            logger.info("[AUTH] Login success: user_id=%s email=%s", user_id, email)
            return {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "bearer",
                "expires_in": jwt_expiry,
            }

    async def _login_client_leadership(
        self,
        ctx: TenantContext,
        user_id: uuid.UUID,
        email: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Login a client-leadership user (Client Director etc.) — D2, D9.

        Queries client_user instead of app_user, validates lifecycle_status == 'active',
        mints a custom HS256 JWT carrying {sub, user_tier, client_id, role_id, exp}.
        """
        from kernel.user.models.client_user import ClientUser
        from kernel.config.resolver import config
        from jose import jwt

        with self._session_factory() as session:
            user_obj = session.get(ClientUser, user_id)
            if not user_obj:
                logger.warning("[AUTH] Login failed: client_user not found user_id=%s", user_id)
                self._record_login_attempt(
                    ctx, email, "login_failure",
                    ip_address=ip_address, user_agent=user_agent,
                )
                raise AuthError("User record missing. Contact administrator.", status_code=403)

            if user_obj.lifecycle_status != "active":
                logger.warning("[AUTH] Login failed: user_id=%s lifecycle=%s",
                               user_id, user_obj.lifecycle_status)
                self._record_login_attempt(
                    ctx, email, "login_failure",
                    user_id=user_id, ip_address=ip_address, user_agent=user_agent,
                )
                raise AuthError(f"Account is not active. Status: {user_obj.lifecycle_status}.", status_code=403)

            self._record_login_attempt(
                ctx, email, "login_success",
                user_id=user_id, ip_address=ip_address, user_agent=user_agent,
            )

            jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "test-secret-for-c01")
            now = datetime.now(timezone.utc)
            jwt_expiry = int(config.get('auth.jwtExpirySeconds') or 3600)

            cd_jwt = jwt.encode({
                "sub": str(user_id),
                "user_tier": "client_leadership",
                "client_id": str(user_obj.client_id),
                "role_id": str(user_obj.role_id),
                "iat": now,
                "exp": now + timedelta(seconds=jwt_expiry),
            }, jwt_secret, algorithm="HS256")

            logger.info("[AUTH] CD login success: user_id=%s client_id=%s", user_id, user_obj.client_id)

            return {
                "access_token": cd_jwt,
                "refresh_token": "",
                "token_type": "bearer",
                "expires_in": jwt_expiry,
                "user_tier": "client_leadership",
                "client_id": str(user_obj.client_id),
            }

    async def refresh(
        self,
        ctx: TenantContext,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Refresh access token using refresh token (D8b, D28a).

        Calls Supabase refresh_token, returns new pair, records token_refresh.
        """
        logger.info("[AUTH] Token refresh attempt: user=%s ip=%s", ctx.user_id, ip_address)
        try:
            result = await self._supabase.refresh_token(refresh_token)
            logger.info("[AUTH] Token refresh success: user=%s", ctx.user_id)
        except SupabaseAuthError as e:
            logger.warning("[AUTH] Token refresh failed: user=%s error=%s", ctx.user_id, str(e)[:100])
            raise AuthError("Invalid or expired refresh token", status_code=401) from e

        # Record token refresh
        self._record_login_attempt(
            ctx, "", "token_refresh",
            ip_address=ip_address, user_agent=user_agent,
        )

        from kernel.config.resolver import config
        jwt_expiry = int(config.get('auth.jwtExpirySeconds') or 3600)

        return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": "bearer",
            "expires_in": jwt_expiry,
        }

    async def logout(
        self,
        ctx: TenantContext,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Revoke refresh token (D17, D28a).

        Calls Supabase revoke_refresh_token, records logout.
        """
        logger.info("[AUTH] Logout attempt: user=%s ip=%s", ctx.user_id, ip_address)
        try:
            await self._supabase.revoke_refresh_token(refresh_token)
            logger.info("[AUTH] Logout success: user=%s", ctx.user_id)
        except SupabaseAuthError as e:
            logger.warning("[AUTH] Logout failed: user=%s error=%s", ctx.user_id, str(e)[:100])
            raise AuthError("Failed to revoke refresh token", status_code=400) from e

        # Record logout
        self._record_login_attempt(
            ctx, "", "logout",
            ip_address=ip_address, user_agent=user_agent,
        )

    async def activate(
        self,
        ctx: TenantContext,
        invite_token: str,
        password: str,
    ) -> dict[str, str]:
        """Accept invite: verify JWT, set password, transition invited → active (D4, D29).

        Verifies invite JWT, checks user not already active, calls Supabase
        update_user(uid, password, email_confirm=true), transitions app_user
        from invited to active.
        """
        logger.info("[AUTH] Activate attempt: invite_token=%s...", invite_token[:20])
        # Verify invite token
        try:
            token_data = verify_invite_token(invite_token)
            logger.info("[AUTH] Invite token verified: user_id=%s email=%s", token_data["user_id"], token_data["email"])
        except InvalidInviteTokenError as e:
            logger.warning("[AUTH] Activate failed: invalid invite token: %s", str(e)[:100])
            raise AuthError(f"Invalid invite token: {e}", status_code=400) from e

        user_id = token_data["user_id"]
        email = token_data["email"]

        with self._session_factory() as session:
            # Look up app_user
            # Look up app_user by UUID — bypass tenant filter for auth operations
            from kernel.user.models.user import User
            from kernel.user.models.client_user import ClientUser
            user_obj = session.get(User, user_id)
            client_user_obj = None
            user_dto = self._user_repo._to_dto(user_obj) if user_obj else None
            
            if not user_dto:
                # Try client_user (client-leadership tier per D2)
                client_user_obj = session.get(ClientUser, user_id)
            
            if not user_dto and not client_user_obj:
                raise AuthError("User not found", status_code=404)

            # Determine target
            target_table = "client_user" if client_user_obj else "app_user"
            target_lifecycle = client_user_obj.lifecycle_status if client_user_obj else user_dto.lifecycle_status

            # Check user not already active
            if target_lifecycle == "active":
                raise AuthError("User is already active", status_code=400)

            # Call Supabase to set password and confirm email
            try:
                await self._supabase.update_user(
                    user_id,
                    password=password,
                    email_confirm=True,
                )
                logger.info("[AUTH] Supabase user updated: user_id=%s", user_id)
            except SupabaseAuthError as e:
                logger.error("[AUTH] Supabase update failed: user_id=%s error=%s", user_id, str(e)[:100])
                raise AuthError(f"Failed to activate user: {e}", status_code=502) from e

            # Transition app_user or client_user from invited to active (D29)
            if client_user_obj:
                # Client-leadership tier — transition client_user
                from kernel.user.models.client_user_lifecycle_event import ClientUserLifecycleEvent
                client_user_obj.lifecycle_status = "active"
                event = ClientUserLifecycleEvent(
                    client_user_id=client_user_obj.id,
                    state="active",
                    reason="Completed invite activation",
                    actor=str(user_id),
                )
                session.add(event)
                session.flush()
                result_lifecycle = client_user_obj.lifecycle_status
            else:
                from kernel.user.services.dtos import UserUpdateDTO
                update_dto = UserUpdateDTO(lifecycle_status="active")
                result = self._user_repo.update(session, ctx, user_id, update_dto)
                result_lifecycle = result.lifecycle_status
            session.commit()

            logger.info("[AUTH] User activated: user_id=%s table=%s lifecycle=%s", user_id, target_table, result_lifecycle)

            # Emit audit event
            self._audit.emit(
                action="user_activated",
                client_id=ctx.client_id,
                institution_id=ctx.institution_id,
                actor=ctx.user_id,
                payload={
                    "user_id": str(user_id),
                    "email": email,
                },
            )

            return {"message": "User activated successfully", "user_id": str(user_id)}

    async def request_otp(
        self,
        ctx: TenantContext,
        email: str,
    ) -> dict[str, str]:
        """Request email OTP (D13).

        Calls Supabase sign_in_with_otp.
        """
        logger.info("[AUTH] OTP request: email=%s ip=%s", email, ip_address)
        try:
            await self._supabase.sign_in_with_otp(email)
            logger.info("[AUTH] OTP sent: email=%s", email)
        except SupabaseAuthError as e:
            logger.error("[AUTH] OTP request failed: email=%s error=%s", email, str(e)[:100])
            raise AuthError(f"Failed to send OTP: {e}", status_code=502) from e

        return {"message": "OTP sent successfully"}

    async def verify_otp(
        self,
        ctx: TenantContext,
        email: str,
        token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Verify OTP, return tokens (D13, D18, D19, D33).

        Calls Supabase verify_otp, same lifecycle + client checks as login,
        returns tokens, records login_success/login_failure.
        """
        logger.info("[AUTH] OTP verify: email=%s ip=%s", email, ip_address)
        try:
            result = await self._supabase.verify_otp(email, token, type="email")
            logger.info("[AUTH] OTP verify success: email=%s", email)
        except SupabaseAuthError as e:
            logger.warning("[AUTH] OTP verify failed: email=%s error=%s", email, str(e)[:100])
            # OTP verification failed — record failure
            self._record_login_attempt(
                ctx, email, "login_failure",
                ip_address=ip_address, user_agent=user_agent,
            )
            raise AuthError("Invalid or expired OTP", status_code=401) from e

        # OTP verification succeeded — look up app_user by UUID (sub)
        supabase_user = result.get("user", {})
        user_id_str = supabase_user.get("id")
        if not user_id_str:
            self._record_login_attempt(
                ctx, email, "login_failure",
                ip_address=ip_address, user_agent=user_agent,
            )
            raise AuthError("User record missing. Contact administrator.", status_code=403)

        user_id = uuid.UUID(user_id_str)

        with self._session_factory() as session:
            # Look up app_user by UUID
            # Look up app_user by UUID — bypass tenant filter for auth operations
            from kernel.user.models.user import User
            user_obj = session.get(User, user_id)
            user_dto = self._user_repo._to_dto(user_obj) if user_obj else None
            if not user_dto:
                self._record_login_attempt(
                    ctx, email, "login_failure",
                    ip_address=ip_address, user_agent=user_agent,
                )
                raise AuthError("User record missing. Contact administrator.", status_code=403)

            # Check lifecycle is active (D18)
            if user_dto.lifecycle_status != "active":
                self._record_login_attempt(
                    ctx, email, "login_failure",
                    user_id=user_id, ip_address=ip_address, user_agent=user_agent,
                )
                raise AuthError(
                    f"Account is not active. Status: {user_dto.lifecycle_status}. Contact administrator.",
                    status_code=403,
                )

            # Check cross-tenant (D19 failure 3)
            if ctx.client_id and user_dto.client_id != ctx.client_id:
                self._record_login_attempt(
                    ctx, email, "login_failure",
                    user_id=user_id, ip_address=ip_address, user_agent=user_agent,
                )
                raise AuthError("Access denied. Account does not belong to this client.", status_code=403)

            # OTP login succeeded — record success
            self._record_login_attempt(
                ctx, email, "login_success",
                user_id=user_id, ip_address=ip_address, user_agent=user_agent,
            )

            from kernel.config.resolver import config
            jwt_expiry = int(config.get('auth.jwtExpirySeconds') or 3600)

            return {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "bearer",
                "expires_in": jwt_expiry,
            }

    async def request_password_reset(
        self,
        ctx: TenantContext,
        email: str,
    ) -> dict[str, str]:
        """Request password reset email (D15).

        Calls Supabase reset_password_for_email.
        """
        logger.info("[AUTH] Password reset request: email=%s", email)
        # Build redirect URL for frontend
        from kernel.config.resolver import config
        redirect_to = config.get('auth.passwordResetRedirectUrl') or "http://localhost:3000/reset-password"

        try:
            await self._supabase.reset_password_for_email(email, redirect_to)
            logger.info("[AUTH] Password reset email sent: email=%s", email)
        except SupabaseAuthError as e:
            logger.error("[AUTH] Password reset failed: email=%s error=%s", email, str(e)[:100])
            raise AuthError(f"Failed to send password reset email: {e}", status_code=502) from e

        return {"message": "Password reset email sent"}

    async def confirm_password_reset(
        self,
        ctx: TenantContext,
        token: str,
        new_password: str,
    ) -> dict[str, str]:
        """Confirm password reset with token (D15).

        Calls Supabase verify_otp(recovery) + update_user(password).
        """
        # We need to get the email from somewhere — for now, we'll assume
        # the token contains enough info or the frontend passes it
        # In Supabase's flow, the recovery token is tied to the user
        # We'll need to decode it or have the frontend pass the email
        # For now, we'll try to verify the OTP with a placeholder email
        # TODO: Fix this — Supabase recovery tokens need email
        raise AuthError("Password reset confirmation not yet implemented", status_code=501)

    async def change_password(
        self,
        ctx: TenantContext,
        current_password: str,
        new_password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, str]:
        """Change password (authenticated) (D16, D16b).

        Calls Supabase sign_in_with_password (re-login), then update_user(password).
        """
        if not ctx.user_id:
            raise AuthError("Authentication required", status_code=401)

        user_id = uuid.UUID(ctx.user_id)

        logger.info("[AUTH] Password change attempt: user=%s", user_id)

        with self._session_factory() as session:
            # Look up app_user to get email
            # Look up app_user by UUID — bypass tenant filter for auth operations
            from kernel.user.models.user import User
            user_obj = session.get(User, user_id)
            user_dto = self._user_repo._to_dto(user_obj) if user_obj else None
            if not user_dto:
                logger.warning("[AUTH] Password change failed: user not found: %s", user_id)
                raise AuthError("User not found", status_code=404)

            email = user_dto.email

        # Re-login with current password to verify (D16b)
        try:
            await self._supabase.sign_in_with_password(email, current_password)
            logger.info("[AUTH] Password change: current password verified for user=%s", user_id)
        except SupabaseAuthError as e:
            logger.warning("[AUTH] Password change failed: wrong current password for user=%s", user_id)
            # Record the re-login attempt
            self._record_login_attempt(
                ctx, email, "login_failure",
                user_id=user_id, ip_address=ip_address, user_agent=user_agent,
            )
            raise AuthError("Current password is incorrect", status_code=401) from e

        # Record the re-login success
        self._record_login_attempt(
            ctx, email, "login_success",
            user_id=user_id, ip_address=ip_address, user_agent=user_agent,
        )

        # Update password via Supabase
        try:
            await self._supabase.update_user(user_id, password=new_password)
        except SupabaseAuthError as e:
            raise AuthError(f"Failed to update password: {e}", status_code=502) from e

        return {"message": "Password changed successfully"}

    def _record_login_attempt(
        self,
        ctx: TenantContext,
        email: str,
        event_type: str,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginAttemptDTO:
        """Record a login attempt (D11, D28a, D33)."""
        with self._session_factory() as session:
            result = self._login_attempt_repo.record(
                session, ctx,
                email=email,
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.commit()
            return result
