"""C-06 Relationship Management — RelationshipType model.

Defines the semantic classification of a Relationship between two Persons.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class RelationshipType(Base):
    """RelationshipType entity — classification of relationships (Mother, Child, Sibling, etc.)."""

    __tablename__ = "relationship_type"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inverse_relationship_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("relationship_type.id"), nullable=True
    )
    is_symmetric: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    inverse = relationship("RelationshipType", remote_side="RelationshipType.id", foreign_keys=[inverse_relationship_type_id])
    compatible_roles = relationship("RelationshipTypeContactRole", back_populates="relationship_type", cascade="all, delete-orphan")
