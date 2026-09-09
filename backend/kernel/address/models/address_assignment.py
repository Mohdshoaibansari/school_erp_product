"""C-13 Address Management — AddressAssignment model."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class AddressAssignment(Base):
    """AddressAssignment entity — associates an entity with an address."""

    __tablename__ = "address_assignment"
    __table_args__ = (
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="chk_assignment_dates"),
        UniqueConstraint("address_id", name="uq_address_assignment_address_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity_type.id"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    address_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("address.id"), nullable=False)
    address_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("address_type.id"), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()")
    )

    # Relationships
    address = relationship("Address")
    address_type = relationship("AddressType")
    entity_type = relationship("EntityType")
