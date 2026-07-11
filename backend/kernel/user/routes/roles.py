"""C-02 RoleAssignment routes (task 9.4).

Endpoints for creating, listing, deleting role assignments.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/role-assignments", tags=["role-assignments"])
