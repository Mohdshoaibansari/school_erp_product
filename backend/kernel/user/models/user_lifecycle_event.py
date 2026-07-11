"""UserLifecycleEvent model (Decision 8, AC-10, AC-11).

Records every lifecycle state transition for a User. One row per transition.
Provides an audit trail of all state changes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class UserLifecycleEvent(Base):
    """User lifecycle event — one row per state transition."""

    __tablename__ = "user_lifecycle_event"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    user = relationship("User", back_populates="lifecycle_events")
