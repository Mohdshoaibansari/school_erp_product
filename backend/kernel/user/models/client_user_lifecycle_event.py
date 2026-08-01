"""ClientUserLifecycleEvent model (D10).

Mirrors user_lifecycle_event but FKs to client_user instead of app_user.
Records every lifecycle transition (invited → active → suspended → archived)
with actor, reason, and timestamp. No client_id column — inherited via the
client_user_id FK.

Fields: id, client_user_id (FK), state, reason, actor, entered_at.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class ClientUserLifecycleEvent(Base):
    """Forensic event log for client_user lifecycle transitions."""

    __tablename__ = "client_user_lifecycle_event"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_user.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
