"""Employee service — application use-cases (D11, D5, D9)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from business.employee.models.employee import (
    Employee,
    EmploymentStatus,
    EmploymentType,
    is_valid_transition,
)
from business.employee.repos.employee_repo import EmployeeRepo
from business.employee.services.dtos import (
    EmployeeCreateRequest,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdateRequest,
    TerminateRequest,
)
from kernel.tenant_context import TenantContext

logger = logging.getLogger(__name__)


def _to_response(e: Employee) -> EmployeeResponse:
    return EmployeeResponse(
        id=e.id,
        client_id=e.client_id,
        institution_id=e.institution_id,
        person_id=e.person_id,
        employee_no=e.employee_no,
        joining_date=e.joining_date,
        employment_type=e.employment_type,
        employment_status=e.employment_status,
        department=e.department,
        designation=e.designation,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


class EmployeeService:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory
        self._repo = EmployeeRepo()

    # ── Create ──────────────────────────────────────────────────
    def create(self, ctx: TenantContext, dto: EmployeeCreateRequest) -> EmployeeResponse:
        from kernel.config.resolver import config

        with self._session_factory() as s:
            allowed_depts = config.get("employee.departments", institution_id=str(ctx.institution_id))
            if dto.department and allowed_depts and dto.department not in allowed_depts:
                raise ValueError(f"Department '{dto.department}' is not in the allowed list")

            allowed_desigs = config.get("employee.designations", institution_id=str(ctx.institution_id))
            if dto.designation and allowed_desigs and dto.designation not in allowed_desigs:
                raise ValueError(f"Designation '{dto.designation}' is not in the allowed list")

            employee_no = self._repo.get_next_employee_number(s, ctx.institution_id)

            emp = Employee(
                client_id=ctx.client_id,
                institution_id=ctx.institution_id,
                person_id=dto.person_id,
                employee_no=employee_no,
                joining_date=dto.joining_date,
                employment_type=dto.employment_type,
                employment_status=EmploymentStatus.HIRED,
                department=dto.department,
                designation=dto.designation,
            )
            emp = self._repo.create(s, emp)
            s.commit()
            logger.info("[EMPLOYEE] Created: id=%s no=%s", emp.id, emp.employee_no)
            return _to_response(emp)

    # ── Get ─────────────────────────────────────────────────────
    def get(self, ctx: TenantContext, employee_id: uuid.UUID) -> EmployeeResponse | None:
        with self._session_factory() as s:
            emp = self._repo.get_by_id(s, employee_id, ctx.institution_id)
            return _to_response(emp) if emp else None

    # ── List ────────────────────────────────────────────────────
    def list_employees(
        self,
        ctx: TenantContext,
        *,
        status: str | None = None,
        employment_type: str | None = None,
        department: str | None = None,
        designation: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> EmployeeListResponse:
        with self._session_factory() as s:
            items, total = self._repo.list_employees(
                s,
                ctx.institution_id,
                status=status,
                employment_type=employment_type,
                department=department,
                designation=designation,
                search=search,
                offset=offset,
                limit=limit,
            )
            return EmployeeListResponse(
                items=[_to_response(e) for e in items],
                total=total,
                offset=offset,
                limit=limit,
            )

    # ── Update ──────────────────────────────────────────────────
    def update(self, ctx: TenantContext, employee_id: uuid.UUID, dto: EmployeeUpdateRequest) -> EmployeeResponse:
        from kernel.config.resolver import config

        with self._session_factory() as s:
            emp = self._repo.get_by_id(s, employee_id, ctx.institution_id)
            if not emp:
                raise ValueError("Employee not found")

            if dto.department is not None:
                allowed_depts = config.get("employee.departments", institution_id=str(ctx.institution_id))
                if allowed_depts and dto.department not in allowed_depts:
                    raise ValueError(f"Department '{dto.department}' is not in the allowed list")
                emp.department = dto.department

            if dto.designation is not None:
                allowed_desigs = config.get("employee.designations", institution_id=str(ctx.institution_id))
                if allowed_desigs and dto.designation not in allowed_desigs:
                    raise ValueError(f"Designation '{dto.designation}' is not in the allowed list")
                emp.designation = dto.designation

            if dto.employment_type is not None:
                emp.employment_type = dto.employment_type
            if dto.joining_date is not None:
                emp.joining_date = dto.joining_date

            emp = self._repo.update(s, emp)
            s.commit()
            return _to_response(emp)

    # ── Transition: activate ────────────────────────────────────
    def activate(self, ctx: TenantContext, employee_id: uuid.UUID) -> EmployeeResponse:
        return self._transition(ctx, employee_id, EmploymentStatus.ACTIVE)

    # ── Transition: suspend ─────────────────────────────────────
    def suspend(self, ctx: TenantContext, employee_id: uuid.UUID) -> EmployeeResponse:
        return self._transition(ctx, employee_id, EmploymentStatus.SUSPENDED)

    # ── Transition: deactivate (on-leave) ───────────────────────
    def deactivate(self, ctx: TenantContext, employee_id: uuid.UUID) -> EmployeeResponse:
        return self._transition(ctx, employee_id, EmploymentStatus.ON_LEAVE)

    # ── Transition: terminate ───────────────────────────────────
    def terminate(self, ctx: TenantContext, employee_id: uuid.UUID, dto: TerminateRequest) -> EmployeeResponse:
        target_map = {
            "resigned": EmploymentStatus.RESIGNED,
            "terminated": EmploymentStatus.TERMINATED,
            "retired": EmploymentStatus.RETIRED,
        }
        target = target_map.get(dto.terminal_status)
        if not target:
            raise ValueError(f"Invalid terminal_status: {dto.terminal_status}")

        return self._transition(ctx, employee_id, target, cascade=True)

    # ── Internal transition helper ──────────────────────────────
    def _transition(
        self,
        ctx: TenantContext,
        employee_id: uuid.UUID,
        target: EmploymentStatus,
        *,
        cascade: bool = False,
    ) -> EmployeeResponse:
        with self._session_factory() as s:
            emp = self._repo.get_by_id(s, employee_id, ctx.institution_id)
            if not emp:
                raise ValueError("Employee not found")

            source = EmploymentStatus(emp.employment_status)
            if not is_valid_transition(source, target):
                raise ValueError(f"Invalid transition: {source.value} → {target.value}")

            emp.employment_status = target.value
            emp = self._repo.update(s, emp)

            if cascade and target.is_terminal:
                self._cascade_archive_account(s, emp)

            s.commit()
            logger.info("[EMPLOYEE] Transition: id=%s %s → %s", emp.id, source.value, target.value)
            return _to_response(emp)

    def _cascade_archive_account(self, s: Session, emp: Employee) -> None:
        """Archive the app_user matching this employee's person + institution (D9)."""
        from kernel.user.models.user import User

        account = s.execute(
            select(User)
            .where(User.person_id == emp.person_id, User.institution_id == emp.institution_id)
        ).scalar_one_or_none()

        if account and account.lifecycle_status != "archived":
            account.lifecycle_status = "archived"
            s.merge(account)
            logger.info("[EMPLOYEE] Cascade: archived app_user id=%s for employee %s", account.id, emp.id)
