"""C-13 Address Management — Tests."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session

from kernel.address.services import AddressService, AddressAssignmentService, GeographicService
from kernel.address.repos import AddressRepo, AddressAssignmentRepo, GeographicRepo, AddressTypeRepo, EntityTypeRepo


class TestAddressValidation:
    """Tests for Address validation and normalization."""

    def test_create_address(self, db: Session):
        """Test creating a valid Address."""
        # Seed geographic data
        geo_repo = GeographicRepo(db)
        country = geo_repo.create_country("IN", "India")
        state = geo_repo.create_state(country.id, "MH", "Maharashtra")
        city = geo_repo.create_city(state.id, "MUMBAI", "Mumbai")

        svc = AddressService(db)
        addr = svc.create_address(
            address_line_1="123 Main St",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )

        assert addr.address_line_1 == "123 Main St"
        assert addr.city_id == city.id

    def test_whitespace_trimming(self, db: Session):
        """Test that whitespace is trimmed."""
        geo_repo = GeographicRepo(db)
        country = geo_repo.create_country("IN", "India")
        state = geo_repo.create_state(country.id, "MH", "Maharashtra")
        city = geo_repo.create_city(state.id, "MUMBAI", "Mumbai")

        svc = AddressService(db)
        addr = svc.create_address(
            address_line_1="  123 Main St  ",
            locality="  MG Road  ",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )

        assert addr.address_line_1 == "123 Main St"
        assert addr.locality == "MG Road"

    def test_optional_blank_normalization(self, db: Session):
        """Test that optional blank values normalize to NULL."""
        geo_repo = GeographicRepo(db)
        country = geo_repo.create_country("IN", "India")
        state = geo_repo.create_state(country.id, "MH", "Maharashtra")
        city = geo_repo.create_city(state.id, "MUMBAI", "Mumbai")

        svc = AddressService(db)
        addr = svc.create_address(
            address_line_1="123 Main St",
            locality="   ",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )

        assert addr.locality is None


class TestGeographicHierarchy:
    """Tests for geographic hierarchy validation."""

    def test_valid_hierarchy(self, db: Session):
        """Test valid city/state/country hierarchy."""
        geo_repo = GeographicRepo(db)
        country = geo_repo.create_country("IN", "India")
        state = geo_repo.create_state(country.id, "MH", "Maharashtra")
        city = geo_repo.create_city(state.id, "MUMBAI", "Mumbai")

        assert geo_repo.validate_hierarchy(city.id, state.id, country.id) is True

    def test_invalid_hierarchy(self, db: Session):
        """Test invalid city/state/country hierarchy."""
        geo_repo = GeographicRepo(db)
        country = geo_repo.create_country("IN", "India")
        state1 = geo_repo.create_state(country.id, "MH", "Maharashtra")
        state2 = geo_repo.create_state(country.id, "KA", "Karnataka")
        city = geo_repo.create_city(state1.id, "MUMBAI", "Mumbai")

        # City belongs to state1, not state2
        assert geo_repo.validate_hierarchy(city.id, state2.id, country.id) is False


class TestAddressTypeCompatibility:
    """Tests for AddressType compatibility."""

    def test_compatible_type(self, db: Session):
        """Test compatible address type."""
        type_repo = AddressTypeRepo(db)
        et_repo = EntityTypeRepo(db)

        et = et_repo.create("PERSON", "Person")
        at = type_repo.create("RESIDENTIAL", "Residential")
        type_repo.add_compatibility(at.id, et.id)

        compatible = type_repo.get_compatible_entity_types(at.id)
        assert et.id in compatible


@pytest.fixture
def db():
    """Mock DB session for unit tests."""
    from unittest.mock import MagicMock
    return MagicMock(spec=Session)
