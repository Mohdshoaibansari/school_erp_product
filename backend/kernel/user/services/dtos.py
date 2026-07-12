"""Pydantic DTOs for the C-02 identity-user domain.

Repos convert ORM → DTO at the boundary. Endpoints accept/respond with DTOs.
ORM objects never cross the repository boundary.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# UserCategory DTOs
# ============================================================

class UserCategoryDTO(BaseModel):
    """Response DTO for a UserCategory."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


# ============================================================
# Role DTOs
# ============================================================

class RoleDTO(BaseModel):
    """Response DTO for a Role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


# ============================================================
# User DTOs
# ============================================================

class UserCreateDTO(BaseModel):
    """Request body for creating a User."""

    email: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    user_category_id: uuid.UUID
    institution_id: uuid.UUID


class UserUpdateDTO(BaseModel):
    """Request body for updating a User."""

    name: str | None = None
    email: str | None = None  # Phase 4 (12.5): email changes propagated to Supabase
    lifecycle_status: str | None = None  # C-03: used by activate endpoint


class UserDTO(BaseModel):
    """Response DTO for a User."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    institution_id: uuid.UUID
    email: str
    name: str
    user_category_id: uuid.UUID
    lifecycle_status: str
    created_at: datetime
    updated_at: datetime


# ============================================================
# UserProfile DTOs
# ============================================================

class UserProfileCreateDTO(BaseModel):
    """Request body for creating a UserProfile."""

    photo: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None


class UserProfileUpdateDTO(BaseModel):
    """Request body for updating a UserProfile."""

    photo: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None


class UserProfileDTO(BaseModel):
    """Response DTO for a UserProfile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    photo: str | None
    date_of_birth: date | None
    gender: str | None
    blood_group: str | None
    created_at: datetime
    updated_at: datetime


# ============================================================
# RoleAssignment DTOs
# ============================================================

class RoleAssignmentCreateDTO(BaseModel):
    """Request body for creating a RoleAssignment."""

    role_id: uuid.UUID
    scope: str | None = None


class RoleAssignmentDTO(BaseModel):
    """Response DTO for a RoleAssignment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    scope: str | None
    created_at: datetime
    updated_at: datetime


# ============================================================
# UserIdentifier DTOs
# ============================================================

class UserIdentifierCreateDTO(BaseModel):
    """Request body for creating a UserIdentifier."""

    type: str = Field(..., min_length=1, max_length=50)
    value: str = Field(..., min_length=1, max_length=100)


class UserIdentifierDTO(BaseModel):
    """Response DTO for a UserIdentifier."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    user_id: uuid.UUID
    type: str
    value: str
    created_at: datetime
    updated_at: datetime


# ============================================================
# UserLifecycleEvent DTOs
# ============================================================

class LifecycleTransitionDTO(BaseModel):
    """Request body for a lifecycle transition."""

    new_state: str | None = None
    reason: str | None = None


class UserLifecycleEventDTO(BaseModel):
    """Response DTO for a UserLifecycleEvent."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    user_id: uuid.UUID
    state: str
    reason: str | None
    actor: str
    entered_at: datetime
