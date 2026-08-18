"""DEPRECATED — user_profile routes removed (T-24, D6a).

The user_profile table was dropped in migration 022. Human data
lives on person (D6a), accessible via UserDTO.person projection.
Standalone person-update endpoint is deferred to the domain-split capability.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/users/{user_id}/profile", tags=["profiles"])


@router.post("")
async def create_profile(user_id: uuid.UUID):
    """Profile endpoints removed — user_profile table dropped (D6a)."""
    raise HTTPException(status_code=404, detail="Profile not found — user_profile table dropped (D6a)")


@router.get("")
async def get_profile(user_id: uuid.UUID):
    """Profile endpoints removed — user_profile table dropped (D6a)."""
    raise HTTPException(status_code=404, detail="Profile not found — user_profile table dropped (D6a)")


@router.patch("")
async def update_profile(user_id: uuid.UUID):
    """Profile endpoints removed — user_profile table dropped (D6a)."""
    raise HTTPException(status_code=404, detail="Profile not found — user_profile table dropped (D6a)")
