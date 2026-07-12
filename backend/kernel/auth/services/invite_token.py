"""Invite token minting and verification (D4, D5, D6, AC-11).

Stateless JWT signed with APP_INVITE_JWT_SECRET. No DB table.
Claims: sub=user_id, email, exp=7d, iss="school-erp/invite".
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt


# Invite JWT secret — separate from Supabase JWT secret (D6)
INVITE_JWT_SECRET = os.environ.get("APP_INVITE_JWT_SECRET", "test-invite-secret-for-c03")
INVITE_JWT_ALGORITHM = "HS256"
INVITE_JWT_ISSUER = "school-erp/invite"
INVITE_JWT_EXPIRY_DAYS = 7


class InvalidInviteTokenError(Exception):
    """Raised when an invite token is invalid, expired, or has wrong issuer."""
    pass


def mint_invite_token(user_id: uuid.UUID, email: str) -> str:
    """Mint an invite JWT (D5).

    Args:
        user_id: the user's UUID.
        email: the user's email.

    Returns:
        JWT string signed with APP_INVITE_JWT_SECRET.
    """
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=INVITE_JWT_EXPIRY_DAYS),
        "iat": datetime.now(timezone.utc),
        "iss": INVITE_JWT_ISSUER,
    }
    return jwt.encode(payload, INVITE_JWT_SECRET, algorithm=INVITE_JWT_ALGORITHM)


def verify_invite_token(token: str) -> dict:
    """Verify an invite JWT (D5).

    Args:
        token: the JWT string.

    Returns:
        dict with user_id (UUID) and email.

    Raises:
        InvalidInviteTokenError: if token is invalid, expired, or has wrong issuer.
    """
    try:
        payload = jwt.decode(
            token,
            INVITE_JWT_SECRET,
            algorithms=[INVITE_JWT_ALGORITHM],
            options={"require": ["exp", "iss", "sub", "email"]},
            issuer=INVITE_JWT_ISSUER,
        )
        return {
            "user_id": uuid.UUID(payload["sub"]),
            "email": payload["email"],
        }
    except JWTError as e:
        raise InvalidInviteTokenError(f"Invalid invite token: {e}") from e


def load_invite_secret() -> str:
    """Load APP_INVITE_JWT_SECRET from env (D6).

    Raises ValueError if the env var is missing.
    Returns the secret value.
    """
    secret = os.environ.get("APP_INVITE_JWT_SECRET")
    if not secret:
        raise ValueError("APP_INVITE_JWT_SECRET environment variable is required")
    return secret
