"""LoginAttempt model (Decision 11, Decision 28a, Decision 33, AC-5, AC-21, AC-22).

Audit record of every login attempt (success/failure). Tenant-scoped via
client_id. user_id is nullable (failed login with unknown email).

Fields: id, client_id (nullable), user_id (nullable), email, event_type,
ip_address, user_agent, occurred_at, created_at.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class LoginAttempt(Base):
    """LoginAttempt table — audit record of auth events."""

    __tablename__ = "login_attempt"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("client.id"), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
