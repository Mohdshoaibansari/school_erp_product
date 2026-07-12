"""FakeSupabaseAuth — in-memory test implementation of SupabaseAuthClient (D23, D24).

Simulates Supabase Auth operations for testing without a live Supabase instance.
Happy-path + documented failure modes only (D24).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from kernel.auth.supabase_client import SupabaseAuthError


class FakeSupabaseAuth:
    """In-memory fake for Supabase Auth (D23, D24).

    Stores users by UUID. Simulates:
    - create_user: add to store; reject duplicate email
    - sign_in_with_password: check password; raise on mismatch
    - sign_in_with_otp: generate OTP; store for verify
    - verify_otp: check OTP; raise on mismatch
    - reset_password_for_email: stash recovery token
    - update_user: apply update; raise if user not found
    - sign_out: clear refresh tokens
    - delete_user: remove from store
    - refresh_token: check valid; return new pair
    - revoke_refresh_token: revoke; future refresh raises
    """

    def __init__(self) -> None:
        # user_id -> {email, password, email_confirmed, refresh_tokens: set}
        self._users: dict[str, dict] = {}
        self._token_counter = 0
        # email -> user_id (for lookup)
        self._email_to_id: dict[str, str] = {}
        # email -> {code, expires_at}
        self._pending_otps: dict[str, dict] = {}
        # email -> {token, expires_at}
        self._pending_resets: dict[str, dict] = {}
        # revoked refresh tokens
        self._revoked_tokens: set[str] = set()

    async def create_user(self, user_id: uuid.UUID, email: str) -> dict:
        uid = str(user_id)
        if email in self._email_to_id:
            raise SupabaseAuthError(f"User with email {email} already exists")
        self._users[uid] = {
            "email": email,
            "password": None,
            "email_confirmed": False,
            "refresh_tokens": set(),
        }
        self._email_to_id[email] = uid
        return {"user": {"id": uid, "email": email}}

    async def sign_in_with_password(self, email: str, password: str) -> dict:
        uid = self._email_to_id.get(email)
        if not uid:
            raise SupabaseAuthError("Invalid credentials")
        user = self._users[uid]
        if user["password"] != password:
            raise SupabaseAuthError("Invalid credentials")
        if not user["email_confirmed"]:
            raise SupabaseAuthError("Email not confirmed")
        self._token_counter += 1
        access_token = f"fake-access-{uid}-{self._token_counter}"
        refresh_token = f"fake-refresh-{uid}-{self._token_counter}"
        user["refresh_tokens"].add(refresh_token)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {"id": uid, "email": email},
        }

    async def sign_in_with_otp(self, email: str) -> dict:
        # Generate a fake OTP
        otp_code = "123456"
        self._pending_otps[email] = {
            "code": otp_code,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        return {"message": "OTP sent"}

    async def verify_otp(self, email: str, token: str, *, type: str = "email") -> dict:
        if type == "email":
            pending = self._pending_otps.get(email)
            if not pending:
                raise SupabaseAuthError("No pending OTP")
            if pending["code"] != token:
                raise SupabaseAuthError("Invalid OTP")
            if datetime.now(timezone.utc) > pending["expires_at"]:
                raise SupabaseAuthError("OTP expired")
            del self._pending_otps[email]
            uid = self._email_to_id.get(email)
            if not uid:
                raise SupabaseAuthError("User not found")
            user = self._users[uid]
            self._token_counter += 1
            access_token = f"fake-access-{uid}-{self._token_counter}"
            refresh_token = f"fake-refresh-{uid}-{self._token_counter}"
            user["refresh_tokens"].add(refresh_token)
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {"id": uid, "email": email},
            }
        elif type == "recovery":
            pending = self._pending_resets.get(email)
            if not pending:
                raise SupabaseAuthError("No pending reset")
            if pending["token"] != token:
                raise SupabaseAuthError("Invalid reset token")
            if datetime.now(timezone.utc) > pending["expires_at"]:
                raise SupabaseAuthError("Reset token expired")
            del self._pending_resets[email]
            uid = self._email_to_id.get(email)
            if not uid:
                raise SupabaseAuthError("User not found")
            user = self._users[uid]
            self._token_counter += 1
            access_token = f"fake-access-{uid}-{self._token_counter}"
            refresh_token = f"fake-refresh-{uid}-{self._token_counter}"
            user["refresh_tokens"].add(refresh_token)
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {"id": uid, "email": email},
            }
        else:
            raise SupabaseAuthError(f"Unknown OTP type: {type}")

    async def reset_password_for_email(self, email: str, redirect_to: str) -> dict:
        uid = self._email_to_id.get(email)
        if not uid:
            # Supabase silently succeeds even for unknown emails
            return {"message": "Password reset email sent"}
        recovery_token = f"fake-recovery-{uid}-{datetime.now(timezone.utc).timestamp()}"
        self._pending_resets[email] = {
            "token": recovery_token,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        return {"message": "Password reset email sent"}

    async def update_user(
        self,
        user_id: uuid.UUID,
        *,
        password: str | None = None,
        email: str | None = None,
        email_confirm: bool | None = None,
    ) -> dict:
        uid = str(user_id)
        if uid not in self._users:
            raise SupabaseAuthError(f"User {uid} not found")
        user = self._users[uid]
        if password is not None:
            user["password"] = password
        if email is not None:
            old_email = user["email"]
            if old_email in self._email_to_id:
                del self._email_to_id[old_email]
            user["email"] = email
            self._email_to_id[email] = uid
        if email_confirm is not None:
            user["email_confirmed"] = email_confirm
        return {"user": {"id": uid, "email": user["email"]}}

    async def sign_out(self, user_id: uuid.UUID, scope: str = "global") -> None:
        uid = str(user_id)
        if uid in self._users:
            self._users[uid]["refresh_tokens"].clear()

    async def delete_user(self, user_id: uuid.UUID) -> None:
        uid = str(user_id)
        if uid in self._users:
            email = self._users[uid]["email"]
            if email in self._email_to_id:
                del self._email_to_id[email]
            del self._users[uid]

    async def refresh_token(self, refresh_token: str) -> dict:
        if refresh_token in self._revoked_tokens:
            raise SupabaseAuthError("Refresh token revoked")
        # Find the user with this refresh token
        for uid, user in self._users.items():
            if refresh_token in user["refresh_tokens"]:
                # Generate new tokens
                self._token_counter += 1
                new_access = f"fake-access-{uid}-{self._token_counter}"
                new_refresh = f"fake-refresh-{uid}-{self._token_counter}"
                # Revoke old, add new
                user["refresh_tokens"].remove(refresh_token)
                self._revoked_tokens.add(refresh_token)
                user["refresh_tokens"].add(new_refresh)
                return {
                    "access_token": new_access,
                    "refresh_token": new_refresh,
                }
        raise SupabaseAuthError("Invalid refresh token")

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        self._revoked_tokens.add(refresh_token)
        # Also remove from user's set
        for uid, user in self._users.items():
            if refresh_token in user["refresh_tokens"]:
                user["refresh_tokens"].discard(refresh_token)
                break
