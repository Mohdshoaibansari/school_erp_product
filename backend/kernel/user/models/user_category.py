"""UserCategory lookup model (Decision 9, R6).

Configurable lookup table for user categories. Default seed data:
Learner, Academic Staff, Academic Leadership, Administrative Staff,
Executive Leadership. Adding a new category is a data insert, not a code change.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class UserCategory(Base):
    """User category lookup table."""

    __tablename__ = "user_category"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
