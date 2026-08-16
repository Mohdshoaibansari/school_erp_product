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

    id: uuid.UUID = Field(..., description="User category unique identifier")
    name: str = Field(..., description="User category name (e.g. Learner, Academic Staff)")


# ============================================================
# Role DTOs
# ============================================================

class RoleDTO(BaseModel):
    """Response DTO for a Role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Role unique identifier")
    name: str = Field(..., description="Role name (e.g. Admin, Teacher, Student)")


# ============================================================
# User DTOs
# ============================================================

class UserCreateDTO(BaseModel):
    """Request body for creating a User."""

    email: str = Field(..., min_length=1, max_length=255, description="User email address (globally unique)")
    name: str = Field(..., min_length=1, max_length=255, description="User display name")
    user_category_id: uuid.UUID = Field(..., description="User category reference (Learner, Academic Staff, etc.)")
    institution_id: uuid.UUID = Field(..., description="Institution reference — every app_user row belongs to exactly one institution (D13)")
    role_id: uuid.UUID | None = Field(None, description="Role assigned atomically at creation (D2)")


class UserUpdateDTO(BaseModel):
    """Request body for updating a User."""

    name: str | None = Field(None, description="New display name")
    email: str | None = Field(None, description="New email address (Phase 4: email changes propagated to Supabase)")
    lifecycle_status: str | None = Field(None, description="User lifecycle state: invited/active/suspended/archived (C-03 activate endpoint)")


class UserDTO(BaseModel):
    """Response DTO for a User."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="User unique identifier")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this user belongs to")
    institution_id: uuid.UUID | None = Field(None, description="Institution reference (nullable for client-level users)")
    email: str = Field(..., description="User email address (globally unique)")
    name: str = Field(..., description="User display name")
    user_category_id: uuid.UUID = Field(..., description="User category reference")
    lifecycle_status: str = Field(..., description="User lifecycle state: invited/active/suspended/archived")
    created_at: datetime = Field(..., description="Timestamp when the user was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


class UserCreateResponseDTO(BaseModel):
    """Response DTO for user creation — includes user + invite_url (D1, D3)."""

    user: UserDTO = Field(..., description="Created user record")
    invite_url: str = Field(..., description="Invite/activation URL for the new user")


# ============================================================
# UserProfile DTOs
# ============================================================

class UserProfileCreateDTO(BaseModel):
    """Request body for creating a UserProfile."""

    photo: str | None = Field(None, description="Profile photo URL or path")
    date_of_birth: date | None = Field(None, description="User date of birth")
    gender: str | None = Field(None, description="User gender")
    blood_group: str | None = Field(None, description="User blood group (e.g. B+)")


class UserProfileUpdateDTO(BaseModel):
    """Request body for updating a UserProfile."""

    photo: str | None = Field(None, description="Profile photo URL or path")
    date_of_birth: date | None = Field(None, description="User date of birth")
    gender: str | None = Field(None, description="User gender")
    blood_group: str | None = Field(None, description="User blood group (e.g. B+)")


class UserProfileDTO(BaseModel):
    """Response DTO for a UserProfile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="UserProfile unique identifier")
    user_id: uuid.UUID = Field(..., description="User reference this profile belongs to")
    photo: str | None = Field(None, description="Profile photo URL or path")
    date_of_birth: date | None = Field(None, description="User date of birth")
    gender: str | None = Field(None, description="User gender")
    blood_group: str | None = Field(None, description="User blood group (e.g. B+)")
    created_at: datetime = Field(..., description="Timestamp when the profile was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


# ============================================================
# RoleAssignment DTOs
# ============================================================

class RoleAssignmentCreateDTO(BaseModel):
    """Request body for creating a RoleAssignment."""

    role_id: uuid.UUID = Field(..., description="Role to assign to the user")
    scope: str | None = Field(None, description="Assignment scope (e.g. institution, tenant)")


class RoleAssignmentDTO(BaseModel):
    """Response DTO for a RoleAssignment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="RoleAssignment unique identifier")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this assignment belongs to")
    user_id: uuid.UUID = Field(..., description="User reference receiving the role")
    role_id: uuid.UUID = Field(..., description="Role reference assigned to the user")
    scope: str | None = Field(None, description="Assignment scope (e.g. institution, tenant)")
    created_at: datetime = Field(..., description="Timestamp when the assignment was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


# ============================================================
# UserIdentifier DTOs
# ============================================================

class UserIdentifierCreateDTO(BaseModel):
    """Request body for creating a UserIdentifier."""

    type: str = Field(..., min_length=1, max_length=50, description="Identifier type (e.g. student_id, admission_number)")
    value: str = Field(..., min_length=1, max_length=100, description="Identifier value (e.g. STU-2026-001)")


class UserIdentifierDTO(BaseModel):
    """Response DTO for a UserIdentifier."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="UserIdentifier unique identifier")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this identifier belongs to")
    user_id: uuid.UUID = Field(..., description="User reference this identifier belongs to")
    type: str = Field(..., description="Identifier type (e.g. student_id, admission_number)")
    value: str = Field(..., description="Identifier value")
    created_at: datetime = Field(..., description="Timestamp when the identifier was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


# ============================================================
# UserLifecycleEvent DTOs
# ============================================================

class LifecycleTransitionDTO(BaseModel):
    """Request body for a lifecycle transition."""

    new_state: str | None = Field(None, description="Target lifecycle state (e.g. active, suspended, archived)")
    reason: str | None = Field(None, description="Reason for the lifecycle transition")


class UserLifecycleEventDTO(BaseModel):
    """Response DTO for a UserLifecycleEvent."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Lifecycle event unique identifier")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this event belongs to")
    user_id: uuid.UUID = Field(..., description="User reference this event belongs to")
    state: str = Field(..., description="Lifecycle state entered by the user")
    reason: str | None = Field(None, description="Reason for the transition, if provided")
    actor: str = Field(..., description="Actor who performed the transition (user id or system)")
    entered_at: datetime = Field(..., description="Timestamp when the state was entered")


# ============================================================
# ClientUser DTOs (client-user-bootstrap)
# ============================================================

class ClientUserCreateDTO(BaseModel):
    """Request body for creating a ClientUser (PO bootstrap)."""

    email: str = Field(..., description="Client user email address")
    name: str = Field(..., description="Client user display name")
    role_id: uuid.UUID = Field(..., description="Role reference for the client user")
    user_category_id: uuid.UUID = Field(..., description="User category reference")
    client_id: uuid.UUID | None = Field(None, description="Client reference (body param for PO who has no client_id in TenantContext)")


class ClientUserUpdateDTO(BaseModel):
    """Request body for updating a ClientUser (name, email)."""

    name: str | None = Field(None, description="New client user display name")
    email: str | None = Field(None, description="New client user email address")


class ClientUserDTO(BaseModel):
    """Response DTO for a ClientUser."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="ClientUser unique identifier")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this user belongs to")
    email: str = Field(..., description="Client user email address")
    name: str = Field(..., description="Client user display name")
    user_category_id: uuid.UUID = Field(..., description="User category reference")
    role_id: uuid.UUID = Field(..., description="Role reference for the client user")
    lifecycle_status: str = Field(..., description="Client user lifecycle state: invited/active/suspended/archived")
    created_at: datetime = Field(..., description="Timestamp when the client user was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


class ClientUserTransitionDTO(BaseModel):
    """Request body for transitioning a ClientUser lifecycle."""

    new_state: str = Field(..., description="Target lifecycle state (e.g. active, suspended, archived)")
    reason: str | None = Field(None, description="Reason for the lifecycle transition")
