"""Pydantic DTOs for the C-03 authentication domain.

Repos convert ORM → DTO at the boundary. Endpoints accept/respond with DTOs.
ORM objects never cross the repository boundary.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# LoginAttempt DTOs
# ============================================================

class LoginAttemptDTO(BaseModel):
    """Response DTO for a LoginAttempt."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Login attempt unique identifier")
    client_id: uuid.UUID | None = Field(None, description="Client tenant scope, if any")
    user_id: uuid.UUID | None = Field(None, description="User account ID, if known")
    email: str = Field(..., description="Email used in the login attempt")
    event_type: str = Field(..., description="Event type (login_success, login_failed, etc.)")
    ip_address: str | None = Field(None, description="Source IP address")
    user_agent: str | None = Field(None, description="User-Agent header value")
    occurred_at: datetime = Field(..., description="When the attempt occurred")
    created_at: datetime = Field(..., description="Record creation timestamp")


class TokenResponseDTO(BaseModel):
    """Response DTO for token responses (D8b)."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type (always bearer)")
    expires_in: int = Field(3600, description="Access token lifetime in seconds")
