"""Pydantic DTOs for the C-02 identity-user domain (person-model revamp).

Repos convert ORM → DTO at the boundary. Endpoints accept/respond with DTOs.
ORM objects never cross the repository boundary.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Person DTOs (NEW — T-09)
# ============================================================

class PersonCreateDTO(BaseModel):
    """Request body for creating a Person (nested in user creation DTOs)."""

    name: str = Field(..., min_length=1, max_length=255, description="Person display name")
    date_of_birth: date | None = Field(None, description="Date of birth")
    gender: str | None = Field(None, description="Gender")
    blood_group: str | None = Field(None, description="Blood group (e.g. B+)")
    photo: str | None = Field(None, description="Profile photo URL or path")
    contact_phone: str | None = Field(None, description="Contact phone number")
    contact_email: str | None = Field(None, description="Contact email address")
    demographics: dict | None = Field(None, description="Extensible demographics (JSON)")


class PersonDTO(BaseModel):
    """Response DTO for a Person."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Person unique identifier")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this person belongs to")
    name: str = Field(..., description="Person display name")
    date_of_birth: date | None = Field(None, description="Date of birth")
    gender: str | None = Field(None, description="Gender")
    blood_group: str | None = Field(None, description="Blood group")
    photo: str | None = Field(None, description="Profile photo URL or path")
    contact_phone: str | None = Field(None, description="Contact phone")
    contact_email: str | None = Field(None, description="Contact email")
    demographics: dict | None = Field(None, description="Extensible demographics (JSON)")
    status: str = Field(..., description="Person status: Active|Inactive|Deceased|ErasureRequested|Anonymized")
    is_minor: bool | None = Field(None, description="Whether the person is a minor")
    is_verified: bool | None = Field(None, description="Whether the person is verified")
    created_at: datetime = Field(..., description="Timestamp when the person was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


# ============================================================
# Role DTOs
# ============================================================

class RoleDTO(BaseModel):
    """Response DTO for a Role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Role unique identifier")
    name: str = Field(..., description="Role name (e.g. Admin, Teacher, Student)")


# ============================================================
# User DTOs (MODIFIED — T-10, T-11)
# ============================================================

class UserCreateDTO(BaseModel):
    """Request body for creating a User (breaking change: person_data replaces name + user_category_id)."""

    email: str = Field(..., min_length=1, max_length=255, description="User email address (globally unique)")
    person_data: PersonCreateDTO = Field(..., description="Person/human data for this user")
    institution_id: uuid.UUID = Field(..., description="Institution reference")
    role_id: uuid.UUID | None = Field(None, description="Role assigned atomically at creation (D2)")


class UserUpdateDTO(BaseModel):
    """Request body for updating a User."""

    name: str | None = Field(None, description="New display name (routed to person)")
    email: str | None = Field(None, description="New email address")
    lifecycle_status: str | None = Field(None, description="User lifecycle state")


class UserDTO(BaseModel):
    """Response DTO for a User (breaking change: person projection replaces name + user_category_id)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="User unique identifier")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this user belongs to")
    institution_id: uuid.UUID | None = Field(None, description="Institution reference")
    email: str = Field(..., description="User email address (globally unique)")
    person: PersonDTO = Field(..., description="Person/human data projection")
    lifecycle_status: str = Field(..., description="User lifecycle state: invited/active/suspended/archived")
    created_at: datetime = Field(..., description="Timestamp when the user was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


class UserCreateResponseDTO(BaseModel):
    """Response DTO for user creation — includes user + invite_url (D1, D3)."""

    user: UserDTO = Field(..., description="Created user record")
    invite_url: str = Field(..., description="Invite/activation URL for the new user")


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
# ClientUser DTOs (MODIFIED — T-12)
# ============================================================

class ClientUserCreateDTO(BaseModel):
    """Request body for creating a ClientUser (breaking: person_data replaces name + user_category_id)."""

    email: str = Field(..., description="Client user email address")
    person_data: PersonCreateDTO = Field(..., description="Person/human data for this client user")
    role_id: uuid.UUID = Field(..., description="Role reference for the client user")
    client_id: uuid.UUID | None = Field(None, description="Client reference (body param for PO)")


class ClientUserUpdateDTO(BaseModel):
    """Request body for updating a ClientUser (name, email)."""

    name: str | None = Field(None, description="New display name (routed to person)")
    email: str | None = Field(None, description="New email address")


class ClientUserDTO(BaseModel):
    """Response DTO for a ClientUser (breaking: person projection replaces name + user_category_id)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="ClientUser unique identifier")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this user belongs to")
    email: str = Field(..., description="Client user email address")
    person: PersonDTO = Field(..., description="Person/human data projection")
    role_id: uuid.UUID = Field(..., description="Role reference for the client user")
    lifecycle_status: str = Field(..., description="Client user lifecycle state: invited/active/suspended/archived")
    created_at: datetime = Field(..., description="Timestamp when the client user was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


class ClientUserTransitionDTO(BaseModel):
    """Request body for transitioning a ClientUser lifecycle."""

    new_state: str = Field(..., description="Target lifecycle state (e.g. active, suspended, archived)")
    reason: str | None = Field(None, description="Reason for the lifecycle transition")
