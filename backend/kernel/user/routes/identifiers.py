"""C-02 UserIdentifier routes (task 9.5).

Endpoints for creating, listing, deleting user identifiers.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/identifiers", tags=["identifiers"])
