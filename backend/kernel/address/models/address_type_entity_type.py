"""C-13 Address Management — AddressTypeEntityType model (compatibility matrix)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class AddressTypeEntityType(Base):
    """AddressTypeEntityType — compatibility matrix."""

    __tablename__ = "address_type_entity_type"
    __table_args__ = (
        UniqueConstraint("address_type_id", "entity_type_id", name="uq_address_type_entity_type"),
    )

    address_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("address_type.id"), primary_key=True
    )
    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entity_type.id"), primary_key=True
    )

    # Relationships
    address_type = relationship("AddressType", back_populates="compatible_entity_types")
    entity_type = relationship("EntityType", back_populates="compatible_address_types")
