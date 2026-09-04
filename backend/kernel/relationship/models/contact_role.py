"""C-06 Relationship Management — ContactRole model.

Represents a responsibility attached to a specific Relationship.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class ContactRole(Base):
    """ContactRole entity — responsibilities like PrimaryGuardian, FinancialResponsible, etc."""

    __tablename__ = "contact_role"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    compatible_types = relationship("RelationshipTypeContactRole", back_populates="contact_role", cascade="all, delete-orphan")
    assignments = relationship("ContactRoleAssignment", back_populates="contact_role")
