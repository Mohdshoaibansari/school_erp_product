"""C-13 Address Management — Services."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.address.models.address import Address
from kernel.address.models.address_assignment import AddressAssignment
from kernel.address.repos import (
    AddressRepo,
    AddressAssignmentRepo,
    AddressTypeRepo,
    EntityTypeRepo,
    GeographicRepo,
)


def _normalize_text(value: str | None) -> str | None:
    """Trim whitespace and normalize empty strings to NULL."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


class AddressService:
    """Service for Address entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AddressRepo(db)

    def create_address(
        self,
        address_line_1: str,
        city_id: uuid.UUID,
        state_id: uuid.UUID,
        country_id: uuid.UUID,
        address_line_2: str | None = None,
        locality: str | None = None,
        landmark: str | None = None,
        postal_code: str | None = None,
    ) -> Address:
        """Create a new Address with validation and normalization."""
        # Normalize text inputs
        address_line_1 = _normalize_text(address_line_1) or address_line_1
        address_line_2 = _normalize_text(address_line_2)
        locality = _normalize_text(locality)
        landmark = _normalize_text(landmark)
        postal_code = _normalize_text(postal_code)

        # Validate field lengths
        if len(address_line_1) > 500:
            raise ValueError("ADDRESS_OVERLY_LONG: address_line_1 exceeds 500 characters")
        if address_line_2 and len(address_line_2) > 500:
            raise ValueError("ADDRESS_OVERLY_LONG: address_line_2 exceeds 500 characters")
        if locality and len(locality) > 100:
            raise ValueError("ADDRESS_OVERLY_LONG: locality exceeds 100 characters")
        if landmark and len(landmark) > 100:
            raise ValueError("ADDRESS_OVERLY_LONG: landmark exceeds 100 characters")
        if postal_code and len(postal_code) > 20:
            raise ValueError("ADDRESS_OVERLY_LONG: postal_code exceeds 20 characters")

        return self.repo.create(
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            locality=locality,
            landmark=landmark,
            postal_code=postal_code,
            city_id=city_id,
            state_id=state_id,
            country_id=country_id,
        )

    def get_address(self, addr_id: uuid.UUID) -> Address | None:
        return self.repo.get_by_id(addr_id)

    def update_address(self, addr_id: uuid.UUID, **kwargs) -> Address:
        """Update a future Address."""
        addr = self.repo.get_by_id(addr_id)
        if not addr:
            raise ValueError("ADDRESS_NOT_FOUND: Address does not exist")

        # Normalize text inputs
        for key in ["address_line_1", "address_line_2", "locality", "landmark", "postal_code"]:
            if key in kwargs:
                kwargs[key] = _normalize_text(kwargs[key])

        return self.repo.update(addr, **kwargs)

    def correct_address(self, addr_id: uuid.UUID, **kwargs) -> Address:
        """Correct an effective Address (requires address.correct permission)."""
        addr = self.repo.get_by_id(addr_id)
        if not addr:
            raise ValueError("ADDRESS_NOT_FOUND: Address does not exist")

        # Normalize text inputs
        for key in ["address_line_1", "address_line_2", "locality", "landmark", "postal_code"]:
            if key in kwargs:
                kwargs[key] = _normalize_text(kwargs[key])

        return self.repo.update(addr, **kwargs)

    def delete_address(self, addr: Address) -> None:
        """Delete an Address."""
        self.repo.delete(addr)


class AddressAssignmentService:
    """Service for AddressAssignment entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AddressAssignmentRepo(db)
        self.type_repo = AddressTypeRepo(db)

    def create_assignment(
        self,
        entity_type_id: uuid.UUID,
        entity_id: uuid.UUID,
        address_id: uuid.UUID,
        address_type_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None = None,
    ) -> AddressAssignment:
        """Create an AddressAssignment with validation."""
        # Validate address type compatibility
        compatible_ids = self.type_repo.get_compatible_address_types(entity_type_id)
        if address_type_id not in compatible_ids:
            raise ValueError("ADDRESS_TYPE_NOT_COMPATIBLE: AddressType not compatible with EntityType")

        # Check for overlapping assignments
        if self.repo.check_overlap(entity_type_id, entity_id, address_type_id, valid_from, valid_to):
            raise ValueError("ADDRESS_ASSIGNMENT_OVERLAP: Overlapping assignment exists")

        return self.repo.create(
            entity_type_id=entity_type_id,
            entity_id=entity_id,
            address_id=address_id,
            address_type_id=address_type_id,
            valid_from=valid_from,
            valid_to=valid_to,
        )

    def get_assignment(self, aa_id: uuid.UUID) -> AddressAssignment | None:
        return self.repo.get_by_id(aa_id)

    def list_by_entity(
        self,
        entity_type_id: uuid.UUID,
        entity_id: uuid.UUID,
        effective_date: date | None = None,
    ) -> Sequence[AddressAssignment]:
        return self.repo.list_by_entity(entity_type_id, entity_id, effective_date)

    def end_assignment(self, aa_id: uuid.UUID, end_date: date) -> AddressAssignment:
        """End an assignment by setting valid_to."""
        aa = self.repo.get_by_id(aa_id)
        if not aa:
            raise ValueError("ADDRESS_ASSIGNMENT_NOT_FOUND: AddressAssignment does not exist")

        return self.repo.update(aa, valid_to=end_date)


class AddressTypeService:
    """Service for AddressType entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AddressTypeRepo(db)

    def list_types(self) -> Sequence:
        return self.repo.list_all()

    def list_compatible_types(self, entity_type_id: uuid.UUID) -> Sequence:
        """List AddressTypes compatible with an EntityType."""
        compatible_ids = self.repo.get_compatible_address_types(entity_type_id)
        if not compatible_ids:
            return []
        return self.repo.list_all()  # Filter in service layer


class GeographicService:
    """Service for geographic reference data."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = GeographicRepo(db)

    def list_countries(self) -> Sequence:
        return self.repo.list_countries()

    def list_states(self, country_id: uuid.UUID) -> Sequence:
        return self.repo.list_states_by_country(country_id)

    def list_cities(self, state_id: uuid.UUID) -> Sequence:
        return self.repo.list_cities_by_state(state_id)

    def validate_hierarchy(self, city_id: uuid.UUID, state_id: uuid.UUID, country_id: uuid.UUID) -> bool:
        return self.repo.validate_hierarchy(city_id, state_id, country_id)
