"""C-02 User CRUD + lifecycle routes (tasks 9.1, 9.2).

Endpoints for creating, reading, updating users and transitioning lifecycle.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.user.dependencies import get_identity_user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/health")
def health() -> dict[str, str]:
    """Health check for C-02 routes."""
    return {"status": "ok", "module": "c02_identity_user_management"}
