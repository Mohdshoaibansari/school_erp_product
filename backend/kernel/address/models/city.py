"""C-13 Address Management — City model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class City(Base):
    """City entity — geographic reference data."""

    __tablename__ = "city"
    __table_args__ = (
        UniqueConstraint("state_id", "code", name="uq_city_state_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    state_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("state.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
