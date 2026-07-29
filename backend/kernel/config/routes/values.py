"""C-08 Configuration Framework — Value CRUD routes (4 endpoints, sync)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from kernel.authz.dependencies import require_permission
from kernel.config.dependencies import get_configuration_service
from kernel.config.services.configuration_service import ConfigurationService
from kernel.tenant_context import TenantContext, get_tenant_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/config/values", tags=["Configuration Values"])


class CreateValueRequest(BaseModel):
    key_id: uuid.UUID
    scope_type: str = Field(..., pattern="^(client|institution)$")
    scope_id: uuid.UUID
    value: Any


class UpdateValueRequest(BaseModel):
    value: Any


def _serialize_value(v: Any) -> dict:
    return {
        "id": str(v.id),
        "key_id": str(v.key_id),
        "scope_type": v.scope_type,
        "scope_id": str(v.scope_id) if v.scope_id else None,
        "client_id": str(v.client_id) if v.client_id else None,
        "institution_id": str(v.institution_id) if v.institution_id else None,
        "value": v.value,
        "created_at": v.created_at.isoformat(),
        "updated_at": v.updated_at.isoformat(),
        "updated_by": str(v.updated_by),
    }


@router.post(
    "",
    summary="Create a configuration value override (role-scope checked)",
)
def create_value(
    body: CreateValueRequest,
    service: ConfigurationService = Depends(get_configuration_service),
    ctx: TenantContext = Depends(get_tenant_context),
    _perm: None = Depends(require_permission("config.value", "create")),
):
    try:
        v = service.create_value(
            key_id=body.key_id,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
            value=body.value,
            actor=ctx,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize_value(v)


@router.get(
    "",
    summary="List configuration value overrides (scoped to caller's role)",
)
def list_values(
    key_id: uuid.UUID | None = Query(default=None),
    scope_type: str | None = Query(default=None),
    scope_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: ConfigurationService = Depends(get_configuration_service),
    ctx: TenantContext = Depends(get_tenant_context),
    _perm: None = Depends(require_permission("config.value", "list")),
):
    client_id_filter: uuid.UUID | None = None
    institution_id_filter: uuid.UUID | None = None

    if not (ctx.is_platform_owner or "platform_owner" in (ctx.roles or [])):
        if "client_director" in (ctx.roles or []) and ctx.client_id:
            client_id_filter = ctx.client_id
        elif "Admin" in (ctx.roles or []) and ctx.institution_id:
            institution_id_filter = ctx.institution_id

    values, total = service.repo.list_values(
        key_id=key_id,
        scope_type=scope_type,
        scope_id=scope_id,
        client_id=client_id_filter,
        institution_id=institution_id_filter,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_value(v) for v in values],
    }


@router.get(
    "/{value_id}",
    summary="Get a single configuration value by ID",
)
def get_value(
    value_id: uuid.UUID,
    service: ConfigurationService = Depends(get_configuration_service),
    _perm: None = Depends(require_permission("config.value", "list")),
):
    v = service.repo.get_value_by_id(value_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Configuration value not found")
    return _serialize_value(v)


@router.patch(
    "/{value_id}",
    summary="Update a configuration value override",
)
def update_value(
    value_id: uuid.UUID,
    body: UpdateValueRequest,
    service: ConfigurationService = Depends(get_configuration_service),
    ctx: TenantContext = Depends(get_tenant_context),
    _perm: None = Depends(require_permission("config.value", "update")),
):
    v = service.update_value(
        value_id,
        value=body.value,
        actor=ctx,
    )
    if v is None:
        raise HTTPException(status_code=404, detail="Configuration value not found")
    return _serialize_value(v)


@router.delete(
    "/{value_id}",
    summary="Delete a configuration value override (falls back to parent scope)",
)
def delete_value(
    value_id: uuid.UUID,
    service: ConfigurationService = Depends(get_configuration_service),
    ctx: TenantContext = Depends(get_tenant_context),
    _perm: None = Depends(require_permission("config.value", "delete")),
):
    deleted = service.delete_value(value_id, actor=ctx)
    if not deleted:
        raise HTTPException(status_code=404, detail="Configuration value not found")
    return {"detail": "Configuration value deleted", "id": str(value_id)}
