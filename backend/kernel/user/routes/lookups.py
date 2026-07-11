"""C-02 lookup routes (task 9.6).

Endpoints for listing UserCategory and Role lookup tables.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/lookups", tags=["lookups"])
