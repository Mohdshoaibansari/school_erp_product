"""Person model — the enduring human anchor (D3a, D6a).

A Person is the human entity, independent of any account. One human = one Person.
A Person may have zero or many app_user/client_user accounts (D3b).
Person carries all human-intrinsic data: name, DOB, gender, blood group,
photo, contact info, demographics, and an orthogonal status classifier (D3c).

Person is role-agnostic (D3d) — no person_type, no classification.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Person(Base):
    """Person table — enduring human anchor."""

    __tablename__ = "person"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(10), nullable=True)
    photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    demographics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(25), nullable=False, server_default="Active")
    is_minor: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    __table_args__ = (
        CheckConstraint(
            "status IN ('Active','Inactive','Deceased','ErasureRequested','Anonymized')",
            name="chk_person_status",
        ),
    )
