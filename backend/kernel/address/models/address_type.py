"""C-13 Address Management — AddressType model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class AddressType(Base):
    """AddressType entity — semantic purpose of an address."""

    __tablename__ = "address_type"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    compatible_entity_types = relationship("AddressTypeEntityType", back_populates="address_type", cascade="all, delete-orphan")
