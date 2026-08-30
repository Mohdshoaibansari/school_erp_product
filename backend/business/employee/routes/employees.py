"""Employee routes — thin FastAPI controllers (D11, D12)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from business.employee.dependencies import get_employee_service
from business.employee.services.dtos import (
    EmployeeCreateRequest,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdateRequest,
    TerminateRequest,
)
from business.employee.services.service import EmployeeService
from kernel.authz.dependencies import require_permission
from kernel.tenant_context import get_tenant_context

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(
    dto: EmployeeCreateRequest,
    _authz: None = Depends(require_permission("employee", "create")),
    ctx=Depends(get_tenant_context),
    svc: EmployeeService = Depends(get_employee_service),
):
    try:
        return svc.create(ctx, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    status: str | None = Query(None),
    employment_type: str | None = Query(None),
    department: str | None = Query(None),
    designation: str | None = Query(None),
    search: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _authz: None = Depends(require_permission("employee", "read")),
    ctx=Depends(get_tenant_context),
    svc: EmployeeService = Depends(get_employee_service),
):
    return svc.list_employees(
        ctx,
        status=status,
        employment_type=employment_type,
        department=department,
        designation=designation,
        search=search,
        offset=offset,
        limit=limit,
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: uuid.UUID,
    _authz: None = Depends(require_permission("employee", "read")),
    ctx=Depends(get_tenant_context),
    svc: EmployeeService = Depends(get_employee_service),
):
    result = svc.get(ctx, employee_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Employee not found")
    return result


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: uuid.UUID,
    dto: EmployeeUpdateRequest,
    _authz: None = Depends(require_permission("employee", "update")),
    ctx=Depends(get_tenant_context),
    svc: EmployeeService = Depends(get_employee_service),
):
    try:
        return svc.update(ctx, employee_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{employee_id}/activate", response_model=EmployeeResponse)
def activate_employee(
    employee_id: uuid.UUID,
    _authz: None = Depends(require_permission("employee", "activate")),
    ctx=Depends(get_tenant_context),
    svc: EmployeeService = Depends(get_employee_service),
):
    try:
        return svc.activate(ctx, employee_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{employee_id}/suspend", response_model=EmployeeResponse)
def suspend_employee(
    employee_id: uuid.UUID,
    _authz: None = Depends(require_permission("employee", "suspend")),
    ctx=Depends(get_tenant_context),
    svc: EmployeeService = Depends(get_employee_service),
):
    try:
        return svc.suspend(ctx, employee_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{employee_id}/deactivate", response_model=EmployeeResponse)
def deactivate_employee(
    employee_id: uuid.UUID,
    _authz: None = Depends(require_permission("employee", "deactivate")),
    ctx=Depends(get_tenant_context),
    svc: EmployeeService = Depends(get_employee_service),
):
    try:
        return svc.deactivate(ctx, employee_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{employee_id}/terminate", response_model=EmployeeResponse)
def terminate_employee(
    employee_id: uuid.UUID,
    dto: TerminateRequest,
    _authz: None = Depends(require_permission("employee", "terminate")),
    ctx=Depends(get_tenant_context),
    svc: EmployeeService = Depends(get_employee_service),
):
    try:
        return svc.terminate(ctx, employee_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
