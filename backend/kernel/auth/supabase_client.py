"""SupabaseAuthClient Protocol + implementations (D21, D23, D24, D26).

Protocol defines the interface for Supabase Auth operations.
Production impl wraps the Supabase SDK. Fake impl is in-memory for testing.
"""

from __future__ import annotations

import os
import uuid
from typing import Protocol, runtime_checkable


@runtime_checkable
class SupabaseAuthClient(Protocol):
    """Protocol for Supabase Auth operations (D21, D26).

    Production impl wraps the Supabase SDK with service_role key.
    Fake impl is in-memory for testing (D23, D24).
    """

    async def create_user(self, user_id: uuid.UUID, email: str) -> dict:
        """Create a user in Supabase Auth (D3).

        Args:
            user_id: the UUID to use for the Supabase Auth user (shared with app_user).
            email: the user's email.

        Returns:
            dict with Supabase user data.

        Raises:
            SupabaseAuthError: if creation fails (e.g., email already exists).
        """
        ...

    async def sign_in_with_password(self, email: str, password: str) -> dict:
        """Sign in with email + password (D8).

        Returns:
            dict with access_token, refresh_token, user data.

        Raises:
            SupabaseAuthError: if credentials are invalid.
        """
        ...

    async def sign_in_with_otp(self, email: str) -> dict:
        """Request an OTP for email-based login (D13).

        Returns:
            dict with Supabase response.
        """
        ...

    async def verify_otp(self, email: str, token: str, *, type: str = "email") -> dict:
        """Verify an OTP token (D13).

        Args:
            email: the user's email.
            token: the OTP code.
            type: the OTP type ('email' for login, 'recovery' for password reset).

        Returns:
            dict with access_token, refresh_token, user data.

        Raises:
            SupabaseAuthError: if OTP is invalid or expired.
        """
        ...

    async def reset_password_for_email(self, email: str, redirect_to: str) -> dict:
        """Request a password reset email (D15).

        Returns:
            dict with Supabase response.
        """
        ...

    async def update_user(
        self,
        user_id: uuid.UUID,
        *,
        password: str | None = None,
        email: str | None = None,
        email_confirm: bool | None = None,
    ) -> dict:
        """Update a user in Supabase Auth (D4, D15, D16, D20b).

        Args:
            user_id: the Supabase Auth user ID.
            password: new password (if changing).
            email: new email (if changing).
            email_confirm: whether to mark email as confirmed.

        Returns:
            dict with updated user data.

        Raises:
            SupabaseAuthError: if update fails.
        """
        ...

    async def sign_out(self, user_id: uuid.UUID, scope: str = "global") -> None:
        """Sign out a user (revoke sessions) (D17, D20b).

        Args:
            user_id: the Supabase Auth user ID.
            scope: 'global' to revoke all sessions.
        """
        ...

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """Delete a user from Supabase Auth (D20b).

        Args:
            user_id: the Supabase Auth user ID.
        """
        ...

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh an access token using a refresh token (D8b).

        Returns:
            dict with new access_token, refresh_token.

        Raises:
            SupabaseAuthError: if refresh token is invalid or revoked.
        """
        ...

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke a refresh token (D17).

        Args:
            refresh_token: the refresh token to revoke.
        """
        ...


class SupabaseAuthError(Exception):
    """Base exception for Supabase Auth operations."""
    pass


class SupabaseAuthClientImpl:
    """Production implementation of SupabaseAuthClient (D21, D22).

    Uses the Supabase Python SDK with the service_role key.
    Loaded from SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars.
    """

    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self._url = supabase_url
        self._key = service_role_key
        # Lazy-init the Supabase client
        self._client = None

    def _get_client(self):
        """Lazy-init the Supabase client."""
        if self._client is None:
            from supabase import create_client
            self._client = create_client(self._url, self._key)
        return self._client

    async def create_user(self, user_id: uuid.UUID, email: str) -> dict:
        client = self._get_client()
        try:
            response = client.auth.admin.create_user({
                "id": str(user_id),
                "email": email,
                "email_confirm": False,
            })
            return {"user": response.user.model_dump() if response.user else None}
        except Exception as e:
            raise SupabaseAuthError(f"Failed to create user: {e}") from e

    async def sign_in_with_password(self, email: str, password: str) -> dict:
        client = self._get_client()
        try:
            response = client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user": response.user.model_dump() if response.user else None,
            }
        except Exception as e:
            raise SupabaseAuthError(f"Invalid credentials: {e}") from e

    async def sign_in_with_otp(self, email: str) -> dict:
        client = self._get_client()
        try:
            response = client.auth.sign_in_with_otp({
                "email": email,
                "options": {"should_create_user": False},
            })
            return {"message": "OTP sent"}
        except Exception as e:
            raise SupabaseAuthError(f"Failed to send OTP: {e}") from e

    async def verify_otp(self, email: str, token: str, *, type: str = "email") -> dict:
        client = self._get_client()
        try:
            response = client.auth.verify_otp({
                "email": email,
                "token": token,
                "type": type,
            })
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user": response.user.model_dump() if response.user else None,
            }
        except Exception as e:
            raise SupabaseAuthError(f"Invalid OTP: {e}") from e

    async def reset_password_for_email(self, email: str, redirect_to: str) -> dict:
        client = self._get_client()
        try:
            response = client.auth.reset_password_for_email(
                email,
                options={"redirect_to": redirect_to},
            )
            return {"message": "Password reset email sent"}
        except Exception as e:
            raise SupabaseAuthError(f"Failed to send reset email: {e}") from e

    async def update_user(
        self,
        user_id: uuid.UUID,
        *,
        password: str | None = None,
        email: str | None = None,
        email_confirm: bool | None = None,
    ) -> dict:
        client = self._get_client()
        try:
            update_data: dict = {}
            if password is not None:
                update_data["password"] = password
            if email is not None:
                update_data["email"] = email
            if email_confirm is not None:
                update_data["email_confirm"] = email_confirm
            response = client.auth.admin.update_user_by_id(str(user_id), update_data)
            return {"user": response.user.model_dump() if response.user else None}
        except Exception as e:
            raise SupabaseAuthError(f"Failed to update user: {e}") from e

    async def sign_out(self, user_id: uuid.UUID, scope: str = "global") -> None:
        client = self._get_client()
        try:
            client.auth.admin.sign_out(str(user_id), scope=scope)
        except Exception as e:
            raise SupabaseAuthError(f"Failed to sign out: {e}") from e

    async def delete_user(self, user_id: uuid.UUID) -> None:
        client = self._get_client()
        try:
            client.auth.admin.delete_user(str(user_id))
        except Exception as e:
            raise SupabaseAuthError(f"Failed to delete user: {e}") from e

    async def refresh_token(self, refresh_token: str) -> dict:
        client = self._get_client()
        try:
            response = client.auth.refresh_session({"refresh_token": refresh_token})
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
            }
        except Exception as e:
            raise SupabaseAuthError(f"Failed to refresh token: {e}") from e

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        # Supabase doesn't have a direct revoke API; sign_out is the mechanism
        # For individual token revocation, we'd need to decode and revoke
        # For now, this is a no-op — sign_out handles revocation
        pass


def create_supabase_auth_client() -> SupabaseAuthClientImpl:
    """Create a SupabaseAuthClientImpl from env vars (D22).

    Raises ValueError if required env vars are missing.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url:
        raise ValueError("SUPABASE_URL environment variable is required")
    if not service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")

    return SupabaseAuthClientImpl(supabase_url, service_role_key)
