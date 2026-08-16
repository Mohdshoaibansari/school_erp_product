"""C-08 Configuration Framework — Resolve debug routes (2 endpoints, sync)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from kernel.authz.dependencies import require_permission
from kernel.config.resolver import config as cfg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/config/resolve", tags=["Configuration Resolve"])


class ResolveRequest(BaseModel):
    key: str = Field(..., min_length=1)
    scope_type: str | None = Field(default=None, pattern="^(platform|client|institution)$")
    scope_id: str | None = None
    institution_id: str | None = None
    client_id: str | None = None


@router.post(
    "",
    summary="Resolve a configuration key for a given scope (returns value + source)",
)
def resolve(
    body: ResolveRequest,
    _perm: None = Depends(require_permission("config.key", "list")),
):
    """Resolve a configuration key for a given scope, returning the value and its source.

    Permission: config.key.list. Walks the scope inheritance chain: institution → client → platform.
    Returns the first matching value along with which scope it came from.
    Useful for debugging configuration resolution. Returns 404 if key does not exist.
    """
    try:
        institution_id = body.institution_id
        client_id = body.client_id
        if body.scope_type == "institution" and body.scope_id:
            institution_id = body.scope_id
        elif body.scope_type == "client" and body.scope_id:
            client_id = body.scope_id
        result = cfg.get_with_source(
            key_name=body.key,
            institution_id=institution_id,
            client_id=client_id,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.get(
    "/{key_name}",
    summary="Quick-lookup resolve by key name (returns value + source)",
)
def resolve_by_key(
    key_name: str,
    institution_id: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    _perm: None = Depends(require_permission("config.key", "list")),
):
    """Quick-lookup resolve a configuration key by name.

    Permission: config.key.list. Convenience endpoint for resolving a key with optional
    institution_id and client_id query params. Returns value + source. Returns 404 if key not found.
    """
    try:
        result = cfg.get_with_source(
            key_name=key_name,
            institution_id=institution_id,
            client_id=client_id,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result
