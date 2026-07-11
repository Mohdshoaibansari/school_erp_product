"""UserIdentifier model (Decision 7, AC-7).

Institution-scoped identifiers (Student ID, Employee ID, Admission Number).
Institution comes from the User record — UserIdentifier does NOT store
institution_id. Identifiers are unique per (institution, type, value) via
User.institution_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class UserIdentifier(Base):
    """User identifier — institution-scoped typed identifiers."""

    __tablename__ = "user_identifier"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    user = relationship("User", back_populates="identifiers")
