"""C-06 Relationship Management — RelationshipTypeContactRole model.

Compatibility matrix defining which ContactRoles are valid for which RelationshipTypes.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class RelationshipTypeContactRole(Base):
    """RelationshipTypeContactRole — compatibility matrix."""

    __tablename__ = "relationship_type_contact_role"
    __table_args__ = (
        UniqueConstraint("relationship_type_id", "contact_role_id", name="uq_rel_type_contact_role"),
    )

    relationship_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("relationship_type.id"), primary_key=True
    )
    contact_role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contact_role.id"), primary_key=True
    )

    # Relationships
    relationship_type = relationship("RelationshipType", back_populates="compatible_roles")
    contact_role = relationship("ContactRole", back_populates="compatible_types")
