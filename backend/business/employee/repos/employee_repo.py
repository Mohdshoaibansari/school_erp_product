"""Employee repository — persistence + auto-number generator (D6, D8)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from business.employee.models.employee import Employee


class EmployeeRepo:
    """Employee persistence layer — scoped by client_id / institution_id."""

    def create(self, session: Session, employee: Employee) -> Employee:
        session.add(employee)
        session.flush()
        return employee

    def get_by_id(
        self, session: Session, employee_id: uuid.UUID, institution_id: uuid.UUID
    ) -> Employee | None:
        return session.execute(
            select(Employee)
            .where(Employee.id == employee_id, Employee.institution_id == institution_id)
        ).scalar_one_or_none()

    def list_employees(
        self,
        session: Session,
        institution_id: uuid.UUID,
        *,
        status: str | None = None,
        employment_type: str | None = None,
        department: str | None = None,
        designation: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Employee], int]:
        stmt = select(Employee).where(Employee.institution_id == institution_id)

        if status:
            stmt = stmt.where(Employee.employment_status == status)
        if employment_type:
            stmt = stmt.where(Employee.employment_type == employment_type)
        if department:
            stmt = stmt.where(Employee.department == department)
        if designation:
            stmt = stmt.where(Employee.designation == designation)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Employee.employee_no.ilike(pattern)
                | Employee.department.ilike(pattern)
                | Employee.designation.ilike(pattern)
            )

        total = session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar() or 0

        rows = list(
            session.execute(stmt.order_by(Employee.created_at.desc()).offset(offset).limit(limit)).scalars()
        )
        return rows, total

    def update(self, session: Session, employee: Employee) -> Employee:
        session.merge(employee)
        session.flush()
        return employee

    def get_next_employee_number(self, session: Session, institution_id: uuid.UUID) -> str:
        """Generate next employee number: EMP-{inst_code}-{seq:06d}."""
        inst_code = str(institution_id).replace("-", "")[:6].upper()

        result = session.execute(
            select(Employee.employee_no)
            .where(Employee.institution_id == institution_id, Employee.employee_no.isnot(None))
            .order_by(Employee.employee_no.desc())
            .limit(1)
            .with_for_update()
        ).scalars().first()

        if result and result.startswith(f"EMP-{inst_code}-"):
            try:
                last_num = int(result.split("-")[-1]) + 1
            except ValueError:
                last_num = 1
        else:
            last_num = 1

        return f"EMP-{inst_code}-{last_num:06d}"
