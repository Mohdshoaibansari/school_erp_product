"""C-08 Configuration Framework — Audit read route (1 endpoint, sync)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from kernel.authz.dependencies import require_permission
from kernel.config.dependencies import get_configuration_service
from kernel.config.services.configuration_service import ConfigurationService
from kernel.tenant_context import TenantContext, get_tenant_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/config/audit", tags=["Configuration Audit"])


@router.get(
    "",
    summary="Read the configuration audit log (filterable, role-scoped)",
)
def list_audit(
    key_id: uuid.UUID | None = Query(default=None),
    scope_type: str | None = Query(default=None),
    scope_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    actor_user_id: uuid.UUID | None = Query(default=None),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: ConfigurationService = Depends(get_configuration_service),
    ctx: TenantContext = Depends(get_tenant_context),
    _perm: None = Depends(require_permission("config.audit", "read")),
):
    rows, total = service.list_audit(
        actor=ctx,
        key_id=key_id,
        scope_type=scope_type,
        scope_id=scope_id,
        action=action,
        actor_user_id=actor_user_id,
        from_ts=from_ts,
        to_ts=to_ts,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(r.id),
                "key_id": str(r.key_id),
                "scope_type": r.scope_type,
                "scope_id": str(r.scope_id) if r.scope_id else None,
                "action": r.action,
                "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
                "actor_role": r.actor_role,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ],
    }
