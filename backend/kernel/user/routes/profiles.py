"""C-02 UserProfile routes (task 9.3).

Endpoints for creating, reading, updating user profiles.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])
