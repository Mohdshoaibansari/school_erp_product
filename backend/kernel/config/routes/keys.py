"""C-08 Configuration Framework — Key CRUD routes (5 endpoints, sync).

- POST   /api/v1/config/keys              (PO: create key)
- GET    /api/v1/config/keys              (all: list, paginated, filterable)
- GET    /api/v1/config/keys/{id}         (all: get one)
- PATCH  /api/v1/config/keys/{id}         (PO: update metadata, deprecate)
- DELETE /api/v1/config/keys/{id}         (PO: returns 405 — soft delete only)
"""

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

router = APIRouter(prefix="/api/v1/config/keys", tags=["Configuration Keys"])


class CreateKeyRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(string|number|boolean|json|date)$")
    default_value: Any
    category: str = Field(..., pattern="^(Business Rules|Display|Academic|Notifications|Feature Toggles|Platform|Integrations)$")
    description: str = Field(..., min_length=1)
    merge_strategy: str = Field(default="replace", pattern="^(replace|append_lists|deep_merge)$")
    module: str | None = None
    is_feature_toggle: bool = False
    allowed_values: Any | None = None


class UpdateKeyRequest(BaseModel):
    default_value: Any | None = None
    description: str | None = None
    merge_strategy: str | None = Field(default=None, pattern="^(replace|append_lists|deep_merge)$")
    category: str | None = Field(default=None, pattern="^(Business Rules|Display|Academic|Notifications|Feature Toggles|Platform|Integrations)$")
    module: str | None = None
    is_feature_toggle: bool | None = None
    allowed_values: Any | None = None
    is_deprecated: bool | None = None
    replacement_key: str | None = None


def _serialize_key(k: Any) -> dict:
    return {
        "id": str(k.id),
        "key": k.key,
        "type": k.type,
        "default_value": k.default_value,
        "merge_strategy": k.merge_strategy,
        "category": k.category,
        "module": k.module,
        "description": k.description,
        "is_feature_toggle": k.is_feature_toggle,
        "is_deprecated": k.is_deprecated,
        "deprecated_at": k.deprecated_at.isoformat() if k.deprecated_at else None,
        "replacement_key": k.replacement_key,
        "allowed_values": k.allowed_values,
        "created_at": k.created_at.isoformat(),
        "updated_at": k.updated_at.isoformat(),
    }


@router.post(
    "",
    response_model=None,
    summary="Create a new configuration key (Platform Owner only)",
)
def create_key(
    body: CreateKeyRequest,
    service: ConfigurationService = Depends(get_configuration_service),
    ctx: TenantContext = Depends(get_tenant_context),
    _perm: None = Depends(require_permission("config.key", "create")),
):
    """Create a new configuration key.

    Permission: config.key.create (Platform Owner only).
    The key name must be globally unique. Returns 400 if key already exists or validation fails.
    """
    try:
        k = service.create_key(
            key_name=body.key,
            key_type=body.type,
            default_value=body.default_value,
            category=body.category,
            description=body.description,
            merge_strategy=body.merge_strategy,
            module=body.module,
            is_feature_toggle=body.is_feature_toggle,
            allowed_values=body.allowed_values,
            actor=ctx,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize_key(k)


@router.get(
    "",
    summary="List configuration keys (paginated, filterable)",
)
def list_keys(
    key: str | None = Query(default=None, description="Filter by exact key name"),
    category: str | None = Query(default=None),
    module: str | None = Query(default=None),
    is_deprecated: bool | None = Query(default=None),
    is_feature_toggle: bool | None = Query(default=None),
    include_deprecated: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: ConfigurationService = Depends(get_configuration_service),
    _perm: None = Depends(require_permission("config.key", "list")),
):
    """List configuration keys with pagination and filtering.

    Permission: config.key.list. Returns paginated results.
    Filter by key name, category, module, deprecation status, or feature toggle status.
    """
    keys, total = service.repo.list_keys(
        key=key,
        category=category,
        module=module,
        is_deprecated=is_deprecated,
        is_feature_toggle=is_feature_toggle,
        include_deprecated=include_deprecated,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_key(k) for k in keys],
    }


@router.get(
    "/{key_id}",
    summary="Get a single configuration key by ID",
)
def get_key(
    key_id: uuid.UUID,
    service: ConfigurationService = Depends(get_configuration_service),
    _perm: None = Depends(require_permission("config.key", "list")),
):
    """Get a single configuration key by ID.

    Permission: config.key.list. Returns 404 if key not found.
    """
    k = service.repo.get_key_by_id(key_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Configuration key not found")
    return _serialize_key(k)


@router.patch(
    "/{key_id}",
    summary="Update a configuration key (metadata, default, deprecate)",
)
def update_key(
    key_id: uuid.UUID,
    body: UpdateKeyRequest,
    service: ConfigurationService = Depends(get_configuration_service),
    ctx: TenantContext = Depends(get_tenant_context),
    _perm: None = Depends(require_permission("config.key", "update")),
):
    """Update a configuration key's metadata.

    Permission: config.key.update (Platform Owner only).
    Can update default_value, description, merge_strategy, category, module, is_feature_toggle, allowed_values.
    To deprecate, set is_deprecated=true with replacement_key. Returns 404 if key not found.
    """
    if body.is_deprecated is True:
        k = service.soft_delete_key(
            key_id,
            replacement_key=body.replacement_key,
            actor=ctx,
        )
    else:
        fields = body.model_dump(exclude_unset=True)
        is_dep = fields.pop("is_deprecated", None)
        repl = fields.pop("replacement_key", None)
        if is_dep is not None and is_dep:
            k = service.soft_delete_key(key_id, replacement_key=repl, actor=ctx)
        elif is_dep is not None and not is_dep:
            raise HTTPException(status_code=400, detail="Cannot un-deprecate a key via PATCH")
        else:
            k = service.update_key(key_id, actor=ctx, **fields)
    if k is None:
        raise HTTPException(status_code=404, detail="Configuration key not found")
    return _serialize_key(k)


@router.delete(
    "/{key_id}",
    summary="Hard delete a key — NOT SUPPORTED. Use PATCH is_deprecated=true instead.",
)
def delete_key(
    key_id: uuid.UUID,
    _perm: None = Depends(require_permission("config.key", "deprecate")),
):
    """Hard delete is NOT supported.

    Returns 405 Method Not Allowed. Use PATCH with is_deprecated=true and replacement_key to soft-delete.
    """
    raise HTTPException(
        status_code=405,
        detail="Hard delete is not supported. Use PATCH with is_deprecated=true and replacement_key to soft-delete.",
    )
