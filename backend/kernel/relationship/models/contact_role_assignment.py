"""C-06 Relationship Management — ContactRoleAssignment model.

Attaches a ContactRole to a Relationship with independent temporal validity.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class ContactRoleAssignment(Base):
    """ContactRoleAssignment entity — attaches a ContactRole to a Relationship."""

    __tablename__ = "contact_role_assignment"
    __table_args__ = (
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="chk_role_dates"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    relationship_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("relationship.id"), nullable=False)
    contact_role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contact_role.id"), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    relationship = relationship("Relationship", back_populates="contact_role_assignments")
    contact_role = relationship("ContactRole", back_populates="assignments")
