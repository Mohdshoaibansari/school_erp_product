"""C-13 Address Management — Address model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Address(Base):
    """Address entity — postal address data."""

    __tablename__ = "address"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    address_line_1: Mapped[str] = mapped_column(String(500), nullable=False)
    address_line_2: Mapped[str | None] = mapped_column(String(500), nullable=True)
    locality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    landmark: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    city_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("city.id"), nullable=False)
    state_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("state.id"), nullable=False)
    country_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("country.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()")
    )

    # Relationships
    city = relationship("City")
    state = relationship("State")
    country = relationship("Country")
