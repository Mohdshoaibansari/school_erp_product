"""Pydantic DTOs for the C-03 authentication domain.

Repos convert ORM → DTO at the boundary. Endpoints accept/respond with DTOs.
ORM objects never cross the repository boundary.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ============================================================
# LoginAttempt DTOs
# ============================================================

class LoginAttemptDTO(BaseModel):
    """Response DTO for a LoginAttempt."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID | None
    user_id: uuid.UUID | None
    email: str
    event_type: str
    ip_address: str | None
    user_agent: str | None
    occurred_at: datetime
    created_at: datetime


class TokenResponseDTO(BaseModel):
    """Response DTO for token responses (D8b)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
