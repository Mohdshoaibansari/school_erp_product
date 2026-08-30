"""Employee domain model — entity, enums, lifecycle rules (D1–D4, D6, D8)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    TEMPORARY = "TEMPORARY"
    INTERN = "INTERN"
    CONSULTANT = "CONSULTANT"


class EmploymentStatus(StrEnum):
    HIRED = "Hired"
    ACTIVE = "Active"
    ON_LEAVE = "On-Leave"
    SUSPENDED = "Suspended"
    RETIRED = "Retired"
    RESIGNED = "Resigned"
    TERMINATED = "Terminated"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_STATUSES


_TERMINAL_STATUSES = frozenset({
    EmploymentStatus.RETIRED,
    EmploymentStatus.RESIGNED,
    EmploymentStatus.TERMINATED,
})

_VALID_TRANSITIONS: dict[EmploymentStatus, set[EmploymentStatus]] = {
    EmploymentStatus.HIRED: {EmploymentStatus.ACTIVE},
    EmploymentStatus.ACTIVE: {
        EmploymentStatus.ON_LEAVE,
        EmploymentStatus.SUSPENDED,
        EmploymentStatus.RETIRED,
        EmploymentStatus.RESIGNED,
        EmploymentStatus.TERMINATED,
    },
    EmploymentStatus.ON_LEAVE: {EmploymentStatus.ACTIVE},
    EmploymentStatus.SUSPENDED: {EmploymentStatus.ACTIVE},
    EmploymentStatus.RETIRED: set(),
    EmploymentStatus.RESIGNED: set(),
    EmploymentStatus.TERMINATED: set(),
}


def is_valid_transition(source: EmploymentStatus, target: EmploymentStatus) -> bool:
    """Return True if source → target is a valid lifecycle transition."""
    return target in _VALID_TRANSITIONS.get(source, set())


class Employee(Base):
    """Employee entity — employment relationship with an institution."""

    __tablename__ = "employee"
    __table_args__ = (
        UniqueConstraint("person_id", "institution_id", name="uq_employee_person_institution"),
        UniqueConstraint("institution_id", "employee_no", name="uq_employee_no_institution"),
        CheckConstraint(
            "employment_type IN ('FULL_TIME','PART_TIME','CONTRACT','TEMPORARY','INTERN','CONSULTANT')",
            name="chk_employee_employment_type",
        ),
        CheckConstraint(
            "employment_status IN ('Hired','Active','On-Leave','Suspended','Retired','Resigned','Terminated')",
            name="chk_employee_employment_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id"), nullable=False)
    employee_no: Mapped[str] = mapped_column(String(20), nullable=False)
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    employment_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="Hired")
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
