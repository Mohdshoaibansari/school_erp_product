"""UserProfile model (Decision 5, AC-5).

Separate table linked 1:1 to User. Fields: id, user_id (FK unique),
photo, date_of_birth, gender, blood_group, created_at, updated_at.
Optional — a User can exist without a UserProfile.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class UserProfile(Base):
    """User profile — extended information."""

    __tablename__ = "user_profile"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), unique=True, nullable=False)
    photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    user = relationship("User", back_populates="profile")
