"""C-06 Relationship Management — DTOs."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


# ============================================================
# RelationshipType DTOs
# ============================================================

class RelationshipTypeCreateDTO(BaseModel):
    code: str = Field(..., description="Unique code, e.g. 'mother'")
    name: str = Field(..., description="Display name, e.g. 'Mother'")
    is_symmetric: bool = Field(False, description="True for symmetric types like Sibling")


class RelationshipTypeDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    code: str = Field(..., description="Unique code")
    name: str = Field(..., description="Display name")
    inverse_relationship_type_id: uuid.UUID | None = Field(None, description="Inverse type reference")
    is_symmetric: bool = Field(..., description="Whether this is a symmetric type")

    class Config:
        from_attributes = True


# ============================================================
# ContactRole DTOs
# ============================================================

class ContactRoleDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    code: str = Field(..., description="Unique code")
    name: str = Field(..., description="Display name")

    class Config:
        from_attributes = True


# ============================================================
# Relationship DTOs
# ============================================================

class RelationshipCreateDTO(BaseModel):
    person_a_id: uuid.UUID = Field(..., description="First person")
    person_b_id: uuid.UUID = Field(..., description="Second person")
    relationship_type_id: uuid.UUID = Field(..., description="RelationshipType")
    valid_from: date = Field(..., description="Start of relationship")
    valid_to: date | None = Field(None, description="End of relationship; NULL = ongoing")


class RelationshipUpdateDTO(BaseModel):
    valid_from: date | None = Field(None, description="New start date")
    valid_to: date | None = Field(None, description="New end date")
    relationship_type_id: uuid.UUID | None = Field(None, description="New relationship type")


class RelationshipDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    person_a_id: uuid.UUID = Field(..., description="First person")
    person_b_id: uuid.UUID = Field(..., description="Second person")
    relationship_type_id: uuid.UUID = Field(..., description="RelationshipType")
    valid_from: date = Field(..., description="Start of relationship")
    valid_to: date | None = Field(None, description="End of relationship")
    normalized_pair: str = Field(..., description="Normalized person pair for uniqueness")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


# ============================================================
# ContactRoleAssignment DTOs
# ============================================================

class ContactRoleAssignmentCreateDTO(BaseModel):
    contact_role_id: uuid.UUID = Field(..., description="ContactRole to assign")
    valid_from: date = Field(..., description="Start of role assignment")
    valid_to: date | None = Field(None, description="End of role assignment; NULL = ongoing")


class ContactRoleAssignmentUpdateDTO(BaseModel):
    valid_from: date | None = Field(None, description="New start date")
    valid_to: date | None = Field(None, description="New end date")


class ContactRoleAssignmentDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    relationship_id: uuid.UUID = Field(..., description="Relationship reference")
    contact_role_id: uuid.UUID = Field(..., description="ContactRole reference")
    valid_from: date = Field(..., description="Start of role assignment")
    valid_to: date | None = Field(None, description="End of role assignment")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
