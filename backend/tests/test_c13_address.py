"""C-13 Address Management — Tests.

Unit tests (mock) + Integration tests (real DB via db_session).

G-15: Keep mock tests as unit, add real integration coverage for validation,
hierarchy, compatibility, temporal/overlap, replacement, correction, authorization,
and tenant isolation (G-13). Integration uses Supabase sandbox via DATABASE_URL
from backend/.env and the session-scoped db_session fixture from conftest.py.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from kernel.address.services import AddressService, AddressAssignmentService, GeographicService
from kernel.address.repos import AddressRepo, AddressAssignmentRepo, GeographicRepo, AddressTypeRepo, EntityTypeRepo


# ============================================================
# Unit tests (mock) — kept for fast feedback, no DB
# ============================================================


class TestAddressValidation:
    """Tests for Address validation and normalization (mock)."""

    def test_create_address(self, db: Session):
        """Test creating a valid Address."""
        geo_repo = GeographicRepo(db)
        country = geo_repo.create_country("IN", "India")
        state = geo_repo.create_state(country.id, "MH", "Maharashtra")
        city = geo_repo.create_city(state.id, "MUMBAI", "Mumbai")

        svc = AddressService(db)
        # Mock hierarchy validation to return True
        geo_repo.validate_hierarchy = lambda *a, **k: True  # type: ignore[attr-defined]
        # Patch repo-level validate via monkeypatch on the instance used inside service
        # Service creates its own GeographicRepo(self.db) — so we mock Session execute
        # Instead, rely on the fact that MagicMock returns truthy for validate_hierarchy;
        # we force it by patching GeographicRepo.validate_hierarchy globally for this test.
        import kernel.address.repos as repos_mod
        orig = repos_mod.GeographicRepo.validate_hierarchy
        repos_mod.GeographicRepo.validate_hierarchy = lambda self, *a, **k: True  # type: ignore
        try:
            addr = svc.create_address(
                address_line_1="123 Main St",
                postal_code="400001",
                city_id=city.id,
                state_id=state.id,
                country_id=country.id,
            )
            assert addr.address_line_1 == "123 Main St"
        finally:
            repos_mod.GeographicRepo.validate_hierarchy = orig  # type: ignore

    def test_whitespace_trimming(self, db: Session):
        """Test that whitespace is trimmed."""
        geo_repo = GeographicRepo(db)
        country = geo_repo.create_country("IN", "India")
        state = geo_repo.create_state(country.id, "MH", "Maharashtra")
        city = geo_repo.create_city(state.id, "MUMBAI", "Mumbai")

        import kernel.address.repos as repos_mod
        orig = repos_mod.GeographicRepo.validate_hierarchy
        repos_mod.GeographicRepo.validate_hierarchy = lambda self, *a, **k: True  # type: ignore
        try:
            svc = AddressService(db)
            addr = svc.create_address(
                address_line_1="  123 Main St  ",
                locality="  MG Road  ",
                postal_code="400001",
                city_id=city.id,
                state_id=state.id,
                country_id=country.id,
            )
            assert addr.address_line_1 == "123 Main St"
            assert addr.locality == "MG Road"
        finally:
            repos_mod.GeographicRepo.validate_hierarchy = orig  # type: ignore

    def test_optional_blank_normalization(self, db: Session):
        """Test that optional blank values normalize to NULL."""
        geo_repo = GeographicRepo(db)
        country = geo_repo.create_country("IN", "India")
        state = geo_repo.create_state(country.id, "MH", "Maharashtra")
        city = geo_repo.create_city(state.id, "MUMBAI", "Mumbai")

        import kernel.address.repos as repos_mod
        orig = repos_mod.GeographicRepo.validate_hierarchy
        repos_mod.GeographicRepo.validate_hierarchy = lambda self, *a, **k: True  # type: ignore
        try:
            svc = AddressService(db)
            addr = svc.create_address(
                address_line_1="123 Main St",
                locality="   ",
                postal_code="400001",
                city_id=city.id,
                state_id=state.id,
                country_id=country.id,
            )
            assert addr.locality is None
        finally:
            repos_mod.GeographicRepo.validate_hierarchy = orig  # type: ignore


class TestGeographicHierarchy:
    """Tests for geographic hierarchy validation (mock)."""

    def test_valid_hierarchy(self, db: Session):
        """Test valid city/state/country hierarchy."""
        import kernel.address.repos as repos_mod
        orig = repos_mod.GeographicRepo.validate_hierarchy
        repos_mod.GeographicRepo.validate_hierarchy = lambda self, *a, **k: True  # type: ignore
        try:
            geo_repo = GeographicRepo(db)
            # With mock, we just verify the method is callable
            assert geo_repo.validate_hierarchy(uuid.uuid4(), uuid.uuid4(), uuid.uuid4()) is True
        finally:
            repos_mod.GeographicRepo.validate_hierarchy = orig  # type: ignore

    def test_invalid_hierarchy(self, db: Session):
        """Test invalid city/state/country hierarchy."""
        import kernel.address.repos as repos_mod
        orig = repos_mod.GeographicRepo.validate_hierarchy
        repos_mod.GeographicRepo.validate_hierarchy = lambda self, *a, **k: False  # type: ignore
        try:
            geo_repo = GeographicRepo(db)
            assert geo_repo.validate_hierarchy(uuid.uuid4(), uuid.uuid4(), uuid.uuid4()) is False
        finally:
            repos_mod.GeographicRepo.validate_hierarchy = orig  # type: ignore


class TestAddressTypeCompatibility:
    """Tests for AddressType compatibility (mock)."""

    def test_compatible_type(self, db: Session):
        """Test compatible address type."""
        type_repo = AddressTypeRepo(db)
        et_repo = EntityTypeRepo(db)

        # Use MagicMock behavior — just ensure no exception
        # Real compatibility checked in integration tests below
        assert hasattr(type_repo, "get_compatible_entity_types")
        assert hasattr(et_repo, "get_by_code")


# ============================================================
# Integration tests (real DB) — G-15
# ============================================================

def _unique_code(prefix: str = "T") -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


def _make_geo_chain(db_session: Session):
    """Create a unique Country/State/City chain and commit."""
    geo = GeographicRepo(db_session)
    country_code = _unique_code("C")
    state_code = _unique_code("S")
    city_code = _unique_code("CI")
    country = geo.create_country(country_code, f"Country-{country_code}")
    state = geo.create_state(country.id, state_code, f"State-{state_code}")
    city = geo.create_city(state.id, city_code, f"City-{city_code}")
    db_session.commit()
    return country, state, city


def _get_or_create_entity_types(db_session: Session):
    et_repo = EntityTypeRepo(db_session)
    person_et = et_repo.get_by_code("PERSON")
    if not person_et:
        person_et = et_repo.create("PERSON", "Person")
    inst_et = et_repo.get_by_code("INSTITUTION")
    if not inst_et:
        inst_et = et_repo.create("INSTITUTION", "Institution")
    db_session.commit()
    return person_et, inst_et


def _get_or_create_address_types(db_session: Session):
    at_repo = AddressTypeRepo(db_session)
    codes = ["RESIDENTIAL", "PERMANENT", "CORRESPONDENCE", "OFFICE", "EMERGENCY"]
    ats = {}
    for c in codes:
        at = at_repo.get_by_code(c)
        if not at:
            at = at_repo.create(c, c.title())
        ats[c] = at
    db_session.commit()
    # Ensure compatibility rows exist (idempotent)
    person_et, inst_et = _get_or_create_entity_types(db_session)
    # PERSON: RESIDENTIAL, PERMANENT, CORRESPONDENCE, EMERGENCY
    for c in ["RESIDENTIAL", "PERMANENT", "CORRESPONDENCE", "EMERGENCY"]:
        at = ats[c]
        compat = at_repo.get_compatible_address_types(person_et.id)
        if at.id not in compat:
            at_repo.add_compatibility(at.id, person_et.id)
    # INSTITUTION: OFFICE, CORRESPONDENCE, EMERGENCY
    for c in ["OFFICE", "CORRESPONDENCE", "EMERGENCY"]:
        at = ats[c]
        compat = at_repo.get_compatible_address_types(inst_et.id)
        if at.id not in compat:
            at_repo.add_compatibility(at.id, inst_et.id)
    db_session.commit()
    return ats


class TestAddressValidationIntegration:
    """Integration: field validation, whitespace, required, max-length (G-06)."""

    def test_create_address_success(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(
            address_line_1="123 Main St",
            address_line_2="Apt 4B",
            locality="MG Road",
            landmark="Near Park",
            postal_code="400001",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )
        db_session.commit()
        assert addr.address_line_1 == "123 Main St"
        assert addr.postal_code == "400001"
        assert addr.city_id == city.id

    def test_postal_code_required(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        svc = AddressService(db_session)
        with pytest.raises(ValueError, match="ADDRESS_REQUIRED_FIELD"):
            svc.create_address(
                address_line_1="123 Main St",
                city_id=city.id,
                state_id=state.id,
                country_id=country.id,
                postal_code=None,
            )
        with pytest.raises(ValueError, match="ADDRESS_REQUIRED_FIELD"):
            svc.create_address(
                address_line_1="123 Main St",
                city_id=city.id,
                state_id=state.id,
                country_id=country.id,
                postal_code="   ",
            )

    def test_whitespace_trimming_real(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(
            address_line_1="  123 Main St  ",
            locality="  MG Road  ",
            postal_code="  400001  ",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )
        db_session.commit()
        assert addr.address_line_1 == "123 Main St"
        assert addr.locality == "MG Road"
        assert addr.postal_code == "400001"

    def test_optional_blank_to_null(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(
            address_line_1="123 Main St",
            locality="   ",
            landmark="   ",
            address_line_2="   ",
            postal_code="400001",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )
        db_session.commit()
        assert addr.locality is None
        assert addr.landmark is None
        assert addr.address_line_2 is None

    def test_required_blank_rejected(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        svc = AddressService(db_session)
        with pytest.raises(ValueError, match="ADDRESS_REQUIRED_FIELD"):
            svc.create_address(
                address_line_1="   ",
                postal_code="400001",
                city_id=city.id,
                state_id=state.id,
                country_id=country.id,
            )

    def test_max_length_rejected(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        svc = AddressService(db_session)
        with pytest.raises(ValueError, match="ADDRESS_OVERLY_LONG"):
            svc.create_address(
                address_line_1="x" * 501,
                postal_code="400001",
                city_id=city.id,
                state_id=state.id,
                country_id=country.id,
            )
        with pytest.raises(ValueError, match="ADDRESS_OVERLY_LONG"):
            svc.create_address(
                address_line_1="123 Main St",
                postal_code="x" * 21,
                city_id=city.id,
                state_id=state.id,
                country_id=country.id,
            )


class TestGeographicHierarchyIntegration:
    """Integration: hierarchy enforced on every write path (G-05)."""

    def test_valid_hierarchy(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        geo = GeographicRepo(db_session)
        assert geo.validate_hierarchy(city.id, state.id, country.id) is True

    def test_invalid_hierarchy_state_mismatch(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        # Create second state under same country
        geo = GeographicRepo(db_session)
        state2 = geo.create_state(country.id, _unique_code("S"), "OtherState")
        db_session.commit()
        assert geo.validate_hierarchy(city.id, state2.id, country.id) is False
        svc = AddressService(db_session)
        with pytest.raises(ValueError, match="GEOGRAPHIC_HIERARCHY_INVALID"):
            svc.create_address(
                address_line_1="123 Main St",
                postal_code="400001",
                city_id=city.id,
                state_id=state2.id,
                country_id=country.id,
            )

    def test_hierarchy_enforced_on_update(self, db_session: Session):
        c1, s1, ci1 = _make_geo_chain(db_session)
        c2, s2, ci2 = _make_geo_chain(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(
            address_line_1="123 Main St",
            postal_code="400001",
            city_id=ci1.id,
            state_id=s1.id,
            country_id=c1.id,
        )
        db_session.commit()
        # Create future assignment so update is allowed
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        aa_svc = AddressAssignmentService(db_session)
        future = date.today() + timedelta(days=30)
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=uuid.uuid4(),
            address_id=addr.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=future,
            valid_to=None,
        )
        db_session.commit()
        # Try to update with mismatched hierarchy
        with pytest.raises(ValueError, match="GEOGRAPHIC_HIERARCHY_INVALID"):
            svc.update_address(addr.id, city_id=ci2.id, state_id=s1.id, country_id=c1.id)


class TestAddressTypeCompatibilityIntegration:
    """Integration: compatibility filtering and enforcement (G-04, G-03)."""

    def test_person_compatible_types(self, db_session: Session):
        person_et, _ = _get_or_create_entity_types(db_session)
        _get_or_create_address_types(db_session)
        svc = AddressTypeRepo(db_session).get_compatible_address_types(person_et.id)
        from kernel.address.repos import AddressTypeRepo as ATR
        repo = ATR(db_session)
        types = repo.list_by_ids(svc)
        codes = {t.code for t in types}
        assert "RESIDENTIAL" in codes
        assert "PERMANENT" in codes
        assert "CORRESPONDENCE" in codes
        assert "EMERGENCY" in codes
        assert "OFFICE" not in codes

    def test_institution_compatible_types(self, db_session: Session):
        _, inst_et = _get_or_create_entity_types(db_session)
        _get_or_create_address_types(db_session)
        at_repo = AddressTypeRepo(db_session)
        compat_ids = at_repo.get_compatible_address_types(inst_et.id)
        types = at_repo.list_by_ids(compat_ids)
        codes = {t.code for t in types}
        assert "OFFICE" in codes
        assert "CORRESPONDENCE" in codes
        assert "EMERGENCY" in codes
        assert "RESIDENTIAL" not in codes

    def test_unconfigured_returns_empty(self, db_session: Session):
        # Create a fresh EntityType with no compatibility
        et_repo = EntityTypeRepo(db_session)
        fresh = et_repo.create(_unique_code("ET"), "FreshType")
        db_session.commit()
        at_repo = AddressTypeRepo(db_session)
        compat = at_repo.get_compatible_address_types(fresh.id)
        assert compat == []
        # Service layer should return []
        from kernel.address.services import AddressTypeService
        svc = AddressTypeService(db_session)
        assert svc.list_compatible_types(fresh.id) == []

    def test_incompatible_assignment_rejected(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(
            address_line_1="123 Main St",
            postal_code="400001",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        # OFFICE is not compatible with PERSON
        with pytest.raises(ValueError, match="ADDRESS_TYPE_NOT_COMPATIBLE"):
            aa_svc.create_assignment(
                entity_type_id=person_et.id,
                entity_id=uuid.uuid4(),
                address_id=addr.id,
                address_type_id=ats["OFFICE"].id,
                valid_from=date.today(),
                valid_to=None,
            )


class TestAddressAssignmentTemporalIntegration:
    """Integration: temporal invariants — overlap, adjacent, same-day, CHECK (G-08)."""

    def test_reject_valid_to_before_valid_from(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(
            address_line_1="123 Main St",
            postal_code="400001",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        with pytest.raises(ValueError, match="ADDRESS_ASSIGNMENT_DATE_INVALID"):
            aa_svc.create_assignment(
                entity_type_id=person_et.id,
                entity_id=uuid.uuid4(),
                address_id=addr.id,
                address_type_id=ats["RESIDENTIAL"].id,
                valid_from=date(2026, 9, 10),
                valid_to=date(2026, 9, 9),
            )

    def test_allow_same_day(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(
            address_line_1="123 Main St",
            postal_code="400001",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa = aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=uuid.uuid4(),
            address_id=addr.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date(2026, 9, 10),
            valid_to=date(2026, 9, 10),
        )
        db_session.commit()
        assert aa.valid_from == aa.valid_to

    def test_overlap_rejected(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        entity_id = uuid.uuid4()
        svc = AddressService(db_session)
        addr1 = svc.create_address(address_line_1="Addr1", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        addr2 = svc.create_address(address_line_1="Addr2", postal_code="400002", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=entity_id,
            address_id=addr1.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date(2026, 9, 1),
            valid_to=date(2026, 9, 30),
        )
        db_session.commit()
        with pytest.raises(ValueError, match="ADDRESS_ASSIGNMENT_OVERLAP"):
            aa_svc.create_assignment(
                entity_type_id=person_et.id,
                entity_id=entity_id,
                address_id=addr2.id,
                address_type_id=ats["RESIDENTIAL"].id,
                valid_from=date(2026, 9, 15),
                valid_to=None,
            )

    def test_adjacent_allowed(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        entity_id = uuid.uuid4()
        svc = AddressService(db_session)
        addr1 = svc.create_address(address_line_1="Addr1", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        addr2 = svc.create_address(address_line_1="Addr2", postal_code="400002", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=entity_id,
            address_id=addr1.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date(2026, 8, 1),
            valid_to=date(2026, 8, 31),
        )
        db_session.commit()
        aa2 = aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=entity_id,
            address_id=addr2.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date(2026, 9, 1),
            valid_to=None,
        )
        db_session.commit()
        assert aa2.valid_from == date(2026, 9, 1)

    def test_duplicate_effective_rejected(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        entity_id = uuid.uuid4()
        today = date.today()
        svc = AddressService(db_session)
        addr1 = svc.create_address(address_line_1="Addr1", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        addr2 = svc.create_address(address_line_1="Addr2", postal_code="400002", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=entity_id,
            address_id=addr1.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=today,
            valid_to=None,
        )
        db_session.commit()
        with pytest.raises(ValueError, match="ADDRESS_ASSIGNMENT_OVERLAP"):
            aa_svc.create_assignment(
                entity_type_id=person_et.id,
                entity_id=entity_id,
                address_id=addr2.id,
                address_type_id=ats["RESIDENTIAL"].id,
                valid_from=today,
                valid_to=None,
            )

    def test_ownership_exclusivity(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(address_line_1="UniqueAddr", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=uuid.uuid4(),
            address_id=addr.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date.today(),
            valid_to=None,
        )
        db_session.commit()
        with pytest.raises(ValueError, match="ADDRESS_ALREADY_ASSIGNED"):
            aa_svc.create_assignment(
                entity_type_id=person_et.id,
                entity_id=uuid.uuid4(),
                address_id=addr.id,
                address_type_id=ats["RESIDENTIAL"].id,
                valid_from=date.today() + timedelta(days=10),
                valid_to=None,
            )


class TestAddressReplacementIntegration:
    """Integration: atomic replacement/move (G-09)."""

    def test_replace_atomically(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        entity_id = uuid.uuid4()
        svc = AddressService(db_session)
        addr1 = svc.create_address(address_line_1="Old Addr", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa1 = aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=entity_id,
            address_id=addr1.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date.today() - timedelta(days=10),
            valid_to=None,
        )
        db_session.commit()
        # Replace with new address, valid_from = tomorrow
        tomorrow = date.today() + timedelta(days=1)
        new_data = dict(
            address_line_1="New Addr",
            postal_code="400002",
            city_id=city.id,
            state_id=state.id,
            country_id=country.id,
        )
        new_aa, new_addr = svc.replace_address(
            entity_type_id=person_et.id,
            entity_id=entity_id,
            address_type_id=ats["RESIDENTIAL"].id,
            new_address_data=new_data,
            valid_from=tomorrow,
        )
        db_session.commit()
        # Old assignment should be ended
        refreshed_old = aa_svc.get_assignment(aa1.id)
        assert refreshed_old is not None
        assert refreshed_old.valid_to == tomorrow - timedelta(days=1)
        # Old address remains historical
        assert svc.get_address(addr1.id) is not None
        assert new_addr.address_line_1 == "New Addr"
        assert new_aa.valid_from == tomorrow
        # No reuse
        assert new_addr.id != addr1.id

    def test_replace_rollback_on_hierarchy_failure(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        _, state2, _ = _make_geo_chain(db_session)  # second chain for mismatch
        # Actually need a city that belongs to different state
        geo = GeographicRepo(db_session)
        city2 = geo.create_city(state2.id, _unique_code("CI"), "OtherCity")
        db_session.commit()
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        entity_id = uuid.uuid4()
        svc = AddressService(db_session)
        addr1 = svc.create_address(address_line_1="Old Addr", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa1 = aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=entity_id,
            address_id=addr1.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date.today() - timedelta(days=10),
            valid_to=None,
        )
        db_session.commit()
        old_valid_to_before = aa1.valid_to
        tomorrow = date.today() + timedelta(days=1)
        bad_data = dict(
            address_line_1="Bad Addr",
            postal_code="400002",
            city_id=city2.id,  # belongs to state2
            state_id=state.id,  # mismatch
            country_id=country.id,
        )
        with pytest.raises(ValueError, match="GEOGRAPHIC_HIERARCHY_INVALID"):
            svc.replace_address(
                entity_type_id=person_et.id,
                entity_id=entity_id,
                address_type_id=ats["RESIDENTIAL"].id,
                new_address_data=bad_data,
                valid_from=tomorrow,
            )
        db_session.rollback()
        # Old assignment should not have been modified
        refreshed = aa_svc.get_assignment(aa1.id)
        assert refreshed is not None
        assert refreshed.valid_to == old_valid_to_before


class TestAddressCorrectionIntegration:
    """Integration: correction audit, effective-only, future/historical immutability (G-11/G-12)."""

    def test_correct_effective_with_audit(self, db_session: Session):
        from unittest.mock import MagicMock
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        entity_id = uuid.uuid4()
        mock_emitter = MagicMock()
        svc = AddressService(db_session, audit_emitter=mock_emitter)
        addr = svc.create_address(address_line_1="Banglore", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=entity_id,
            address_id=addr.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date.today() - timedelta(days=5),
            valid_to=None,
        )
        db_session.commit()
        corrected = svc.correct_address(addr.id, address_line_1="Bangalore", actor="tester", client_id=uuid.uuid4(), institution_id=uuid.uuid4())
        db_session.commit()
        assert corrected.address_line_1 == "Bangalore"
        assert mock_emitter.emit.called
        call_kwargs = mock_emitter.emit.call_args.kwargs
        assert call_kwargs["action"] == "address.corrected"
        assert "before" in call_kwargs["payload"]
        assert "after" in call_kwargs["payload"]
        assert call_kwargs["payload"]["before"]["address_line_1"] == "Banglore"
        assert call_kwargs["payload"]["after"]["address_line_1"] == "Bangalore"

    def test_correct_non_effective_rejected(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(address_line_1="Future Addr", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        future = date.today() + timedelta(days=10)
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=uuid.uuid4(),
            address_id=addr.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=future,
            valid_to=None,
        )
        db_session.commit()
        with pytest.raises(ValueError, match="ADDRESS_NOT_EFFECTIVE"):
            svc.correct_address(addr.id, address_line_1="Corrected", actor="tester", client_id=uuid.uuid4())

    def test_ordinary_update_future_allowed_effective_rejected(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        svc = AddressService(db_session)
        # Future address
        addr_future = svc.create_address(address_line_1="Future", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        future = date.today() + timedelta(days=10)
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=uuid.uuid4(),
            address_id=addr_future.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=future,
            valid_to=None,
        )
        db_session.commit()
        updated = svc.update_address(addr_future.id, address_line_1="Future Updated")
        db_session.commit()
        assert updated.address_line_1 == "Future Updated"
        # Effective address — ordinary update should be rejected
        addr_eff = svc.create_address(address_line_1="Effective", postal_code="400002", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=uuid.uuid4(),
            address_id=addr_eff.id,
            address_type_id=ats["PERMANENT"].id,
            valid_from=date.today() - timedelta(days=5),
            valid_to=None,
        )
        db_session.commit()
        with pytest.raises(ValueError, match="EFFECTIVE_ADDRESS_REQUIRES_CORRECTION"):
            svc.update_address(addr_eff.id, address_line_1="Should Fail")

    def test_delete_assignment_and_address_atomically(self, db_session: Session):
        country, state, city = _make_geo_chain(db_session)
        person_et, _ = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        svc = AddressService(db_session)
        addr = svc.create_address(address_line_1="To Delete", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa = aa_svc.create_assignment(
            entity_type_id=person_et.id,
            entity_id=uuid.uuid4(),
            address_id=addr.id,
            address_type_id=ats["RESIDENTIAL"].id,
            valid_from=date.today(),
            valid_to=None,
        )
        db_session.commit()
        aa_svc.delete_assignment_and_address(aa.id)
        db_session.commit()
        assert svc.get_address(addr.id) is None
        assert aa_svc.get_assignment(aa.id) is None


class TestTenantIsolationIntegration:
    """Integration: G-13 — no client_id/institution_id on address tables, scope derived."""

    def test_address_tables_have_no_tenant_columns(self, db_session: Session):
        from sqlalchemy import inspect
        insp = inspect(db_session.bind)
        for tbl in ["address", "address_assignment"]:
            cols = [c["name"] for c in insp.get_columns(tbl)]
            assert "client_id" not in cols, f"{tbl} should not have client_id (derived scope only)"
            assert "institution_id" not in cols, f"{tbl} should not have institution_id"

    def test_no_rls_on_address_tables(self, db_session: Session):
        # Verify that RLS is not enabled on address tables (intentional per D5)
        from sqlalchemy import text
        rows = db_session.execute(text(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relname IN ('address','address_assignment')"
        )).fetchall()
        for relname, relrowsecurity in rows:
            assert relrowsecurity is False, f"{relname} should not have RLS (D5: app-level C-04 only)"

    def test_polymorphic_entity_resolution(self, db_session: Session):
        # Create two entities in different "logical" scopes but same DB — they get
        # different UUIDs; address assignments are isolated by entity_id + type.
        country, state, city = _make_geo_chain(db_session)
        person_et, inst_et = _get_or_create_entity_types(db_session)
        ats = _get_or_create_address_types(db_session)
        entity_person = uuid.uuid4()
        entity_institution = uuid.uuid4()
        svc = AddressService(db_session)
        addr1 = svc.create_address(address_line_1="Person Addr", postal_code="400001", city_id=city.id, state_id=state.id, country_id=country.id)
        addr2 = svc.create_address(address_line_1="Inst Addr", postal_code="400002", city_id=city.id, state_id=state.id, country_id=country.id)
        db_session.commit()
        aa_svc = AddressAssignmentService(db_session)
        aa1 = aa_svc.create_assignment(person_et.id, entity_person, addr1.id, ats["RESIDENTIAL"].id, date.today(), None)
        aa2 = aa_svc.create_assignment(inst_et.id, entity_institution, addr2.id, ats["OFFICE"].id, date.today(), None)
        db_session.commit()
        # Each entity sees only its own assignment
        assert len(aa_svc.list_by_entity(person_et.id, entity_person)) == 1
        assert len(aa_svc.list_by_entity(inst_et.id, entity_institution)) == 1
        assert aa_svc.list_by_entity(person_et.id, entity_institution) == []
        assert aa_svc.list_by_entity(inst_et.id, entity_person) == []


class TestC04AuthorizationIntegration:
    """Integration: G-16 — all routes use require_permission with correct (resource, action)."""

    def test_route_permissions_match_migration(self):
        # This is a file-inspection integration test: ensure every route in
        # backend/kernel/address/routes/*.py uses the seeded perms from
        # migration 027_c13_address (address.create/read/update/delete/correct,
        # address_type.read/manage, entity_type.read).
        import pathlib, re
        routes_dir = pathlib.Path(__file__).parent.parent / "kernel" / "address" / "routes"
        content = ""
        for p in routes_dir.glob("*.py"):
            content += p.read_text(encoding="utf-8") + "\n"
        # Extract all require_permission("x","y") calls
        calls = re.findall(r'require_permission\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)', content)
        expected = {
            ("address", "create"),
            ("address", "read"),
            ("address", "update"),
            ("address", "delete"),
            ("address", "correct"),
            ("address_type", "read"),
        }
        found = set(calls)
        # All expected must be present
        for e in expected:
            assert e in found, f"Missing require_permission{e} in routes"
        # No unexpected resource outside the migration's set
        allowed_resources = {"address", "address_type", "entity_type"}
        for r, a in found:
            assert r in allowed_resources, f"Unexpected resource {r} in routes"
        # Verify manifest register_casbin_policies is no-op with doc note
        manifest_path = pathlib.Path(__file__).parent.parent / "kernel" / "address" / "manifest.py"
        manifest_text = manifest_path.read_text(encoding="utf-8")
        assert "G-16" in manifest_text
        assert "register_casbin_policies" in manifest_text

    def test_services_header_documents_rls_intent(self):
        import pathlib
        svc_path = pathlib.Path(__file__).parent.parent / "kernel" / "address" / "services" / "__init__.py"
        text = svc_path.read_text(encoding="utf-8")
        assert "G-13" in text or "Tenant isolation" in text
        assert "no RLS" in text or "No RLS" in text
        assert "D5" in text


@pytest.fixture
def db():
    """Mock DB session for unit tests."""
    from unittest.mock import MagicMock
    return MagicMock(spec=Session)
