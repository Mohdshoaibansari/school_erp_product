"""C-06 Relationship Management — Relationship model.

Connects exactly two different Persons with temporal validity.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Relationship(Base):
    """Relationship entity — connects two Persons with a RelationshipType."""

    __tablename__ = "relationship"
    __table_args__ = (
        CheckConstraint("person_a_id != person_b_id", name="chk_no_self_relationship"),
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="chk_relationship_dates"),
        UniqueConstraint("normalized_pair", name="uq_normalized_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    person_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id"), nullable=False)
    person_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id"), nullable=False)
    relationship_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("relationship_type.id"), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    normalized_pair: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    person_a = relationship("Person", foreign_keys=[person_a_id])
    person_b = relationship("Person", foreign_keys=[person_b_id])
    relationship_type = relationship("RelationshipType")
    contact_role_assignments = relationship("ContactRoleAssignment", back_populates="relationship", cascade="all, delete-orphan")
