"""C-13 Address Management — DTOs."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


# ============================================================
# EntityType DTOs
# ============================================================

class EntityTypeDTO(BaseModel):
    id: uuid.UUID
    code: str
    name: str

    class Config:
        from_attributes = True


# ============================================================
# AddressType DTOs
# ============================================================

class AddressTypeDTO(BaseModel):
    id: uuid.UUID
    code: str
    name: str

    class Config:
        from_attributes = True


# ============================================================
# Address DTOs
# ============================================================

class AddressCreateDTO(BaseModel):
    address_line_1: str = Field(..., max_length=500)
    address_line_2: str | None = Field(None, max_length=500)
    locality: str | None = Field(None, max_length=100)
    landmark: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    city_id: uuid.UUID
    state_id: uuid.UUID
    country_id: uuid.UUID


class AddressUpdateDTO(BaseModel):
    address_line_1: str | None = Field(None, max_length=500)
    address_line_2: str | None = Field(None, max_length=500)
    locality: str | None = Field(None, max_length=100)
    landmark: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    city_id: uuid.UUID | None = None
    state_id: uuid.UUID | None = None
    country_id: uuid.UUID | None = None


class AddressDTO(BaseModel):
    id: uuid.UUID
    address_line_1: str
    address_line_2: str | None
    locality: str | None
    landmark: str | None
    postal_code: str | None
    city_id: uuid.UUID
    state_id: uuid.UUID
    country_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# AddressAssignment DTOs
# ============================================================

class AddressAssignmentCreateDTO(BaseModel):
    entity_type_id: uuid.UUID
    entity_id: uuid.UUID
    address_id: uuid.UUID
    address_type_id: uuid.UUID
    valid_from: date
    valid_to: date | None = None


class AddressAssignmentDTO(BaseModel):
    id: uuid.UUID
    entity_type_id: uuid.UUID
    entity_id: uuid.UUID
    address_id: uuid.UUID
    address_type_id: uuid.UUID
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Geographic DTOs
# ============================================================

class CountryDTO(BaseModel):
    id: uuid.UUID
    code: str
    name: str

    class Config:
        from_attributes = True


class StateDTO(BaseModel):
    id: uuid.UUID
    country_id: uuid.UUID
    code: str
    name: str

    class Config:
        from_attributes = True


class CityDTO(BaseModel):
    id: uuid.UUID
    state_id: uuid.UUID
    code: str
    name: str

    class Config:
        from_attributes = True
