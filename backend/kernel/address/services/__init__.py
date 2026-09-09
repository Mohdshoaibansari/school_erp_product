"""C-13 Address Management — Services.

Tenant isolation (G-13 / D4-D5): Address and AddressAssignment have NO client_id /
institution_id columns and NO RLS. Scope is derived: service resolves the target
entity via (entity_type_id + entity_id) → Person (→ institution_id → client_id)
or Institution (→ client_id), then builds ResourceContext and delegates to C-04
Casbin. C-04 app-level authorization is the sole decision-maker in Phase 1;
no RLS on address tables is intentional per design D5 (deferred additive later).
Polymorphic entity_id cannot bypass isolation — entity existence + scope
resolution runs before every C-13 operation; same/different institution/client
and Platform Owner cases are covered by C-04 policy.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
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
from kernel.audit import AuditEmitter, DefaultAuditEmitter


def _normalize_text(value: str | None) -> str | None:
    """Trim whitespace and normalize empty strings to NULL."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _address_snapshot(addr: Address) -> dict:
    """Capture before/after dict for audit (JSON-serializable)."""
    return {
        "id": str(addr.id),
        "address_line_1": addr.address_line_1,
        "address_line_2": addr.address_line_2,
        "locality": addr.locality,
        "landmark": addr.landmark,
        "postal_code": addr.postal_code,
        "city_id": str(addr.city_id),
        "state_id": str(addr.state_id),
        "country_id": str(addr.country_id),
    }


class AddressService:
    """Service for Address entity."""

    def __init__(self, db: Session, audit_emitter: AuditEmitter | None = None):
        self.db = db
        self.repo = AddressRepo(db)
        self._audit: AuditEmitter = audit_emitter or DefaultAuditEmitter()

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
        # Normalize text inputs — trim only, never truncate
        address_line_1_norm = _normalize_text(address_line_1)
        address_line_2_norm = _normalize_text(address_line_2)
        locality_norm = _normalize_text(locality)
        landmark_norm = _normalize_text(landmark)
        postal_code_norm = _normalize_text(postal_code)

        # Required field checks — blank/whitespace -> ADDRESS_REQUIRED_FIELD
        if not address_line_1_norm:
            raise ValueError("ADDRESS_REQUIRED_FIELD: address_line_1 is required")
        if not postal_code_norm:
            raise ValueError("ADDRESS_REQUIRED_FIELD: postal_code is required")

        # Validate field lengths — no silent truncation
        if len(address_line_1_norm) > 500:
            raise ValueError("ADDRESS_OVERLY_LONG: address_line_1 exceeds 500 characters")
        if address_line_2_norm and len(address_line_2_norm) > 500:
            raise ValueError("ADDRESS_OVERLY_LONG: address_line_2 exceeds 500 characters")
        if locality_norm and len(locality_norm) > 100:
            raise ValueError("ADDRESS_OVERLY_LONG: locality exceeds 100 characters")
        if landmark_norm and len(landmark_norm) > 100:
            raise ValueError("ADDRESS_OVERLY_LONG: landmark exceeds 100 characters")
        if len(postal_code_norm) > 20:
            raise ValueError("ADDRESS_OVERLY_LONG: postal_code exceeds 20 characters")

        # Enforce geographic hierarchy — immutable reference data
        geo_repo = GeographicRepo(self.db)
        if not geo_repo.validate_hierarchy(city_id, state_id, country_id):
            raise ValueError("GEOGRAPHIC_HIERARCHY_INVALID: City/State/Country hierarchy is invalid")

        return self.repo.create(
            address_line_1=address_line_1_norm,
            address_line_2=address_line_2_norm,
            locality=locality_norm,
            landmark=landmark_norm,
            postal_code=postal_code_norm,
            city_id=city_id,
            state_id=state_id,
            country_id=country_id,
        )

    def get_address(self, addr_id: uuid.UUID) -> Address | None:
        return self.repo.get_by_id(addr_id)

    def update_address(self, addr_id: uuid.UUID, **kwargs) -> Address:
        """Update a future Address. G-11: reject effective/historical via ordinary PATCH."""
        addr = self.repo.get_by_id(addr_id)
        if not addr:
            raise ValueError("ADDRESS_NOT_FOUND: Address does not exist")

        # G-11: enforce ordinary update vs correction separation via AddressAssignment
        aa_repo = AddressAssignmentRepo(self.db)
        assignment = aa_repo.get_by_address_id(addr_id)
        if assignment is not None:
            today = date.today()
            valid_from = assignment.valid_from
            valid_to = assignment.valid_to
            is_effective = valid_from <= today and (valid_to is None or today <= valid_to)
            if is_effective:
                raise ValueError(
                    "EFFECTIVE_ADDRESS_REQUIRES_CORRECTION: effective addresses cannot be modified via ordinary update; use POST /addresses/{id}/correct with address.correct permission"
                )
            is_historical = valid_to is not None and today > valid_to
            if is_historical:
                raise ValueError(
                    "HISTORICAL_ADDRESS_IMMUTABLE: historical addresses cannot be modified via ordinary update"
                )
            # future (today < valid_from) -> allowed; no assignment -> allowed

        # Normalize text inputs — trim only, never truncate
        for key in ["address_line_1", "address_line_2", "locality", "landmark", "postal_code"]:
            if key in kwargs:
                kwargs[key] = _normalize_text(kwargs[key])

        # Field validation: required blanks -> ADDRESS_REQUIRED_FIELD, max lengths
        if "address_line_1" in kwargs:
            if not kwargs["address_line_1"]:
                raise ValueError("ADDRESS_REQUIRED_FIELD: address_line_1 is required")
            if len(kwargs["address_line_1"]) > 500:
                raise ValueError("ADDRESS_OVERLY_LONG: address_line_1 exceeds 500 characters")
        if "postal_code" in kwargs:
            if not kwargs["postal_code"]:
                raise ValueError("ADDRESS_REQUIRED_FIELD: postal_code is required")
            if len(kwargs["postal_code"]) > 20:
                raise ValueError("ADDRESS_OVERLY_LONG: postal_code exceeds 20 characters")
        if "address_line_2" in kwargs and kwargs["address_line_2"] is not None and len(kwargs["address_line_2"]) > 500:
            raise ValueError("ADDRESS_OVERLY_LONG: address_line_2 exceeds 500 characters")
        if "locality" in kwargs and kwargs["locality"] is not None and len(kwargs["locality"]) > 100:
            raise ValueError("ADDRESS_OVERLY_LONG: locality exceeds 100 characters")
        if "landmark" in kwargs and kwargs["landmark"] is not None and len(kwargs["landmark"]) > 100:
            raise ValueError("ADDRESS_OVERLY_LONG: landmark exceeds 100 characters")

        # Enforce geographic hierarchy if any geo field is being changed
        if any(k in kwargs for k in ("city_id", "state_id", "country_id")):
            effective_city_id = kwargs.get("city_id", addr.city_id)
            effective_state_id = kwargs.get("state_id", addr.state_id)
            effective_country_id = kwargs.get("country_id", addr.country_id)
            geo_repo = GeographicRepo(self.db)
            if not geo_repo.validate_hierarchy(effective_city_id, effective_state_id, effective_country_id):
                raise ValueError("GEOGRAPHIC_HIERARCHY_INVALID: City/State/Country hierarchy is invalid")

        return self.repo.update(addr, **kwargs)

    def correct_address(self, addr_id: uuid.UUID, **kwargs) -> Address:
        """Correct an effective Address (requires address.correct permission). G-12: effective-only + audit."""
        # Extract optional audit context (route may pass TenantContext fields)
        actor = kwargs.pop("actor", None)
        client_id = kwargs.pop("client_id", None)
        institution_id = kwargs.pop("institution_id", None)
        # Support private-key variants
        if actor is None:
            actor = kwargs.pop("_actor", None)
        if client_id is None:
            client_id = kwargs.pop("_client_id", None)
        if institution_id is None:
            institution_id = kwargs.pop("_institution_id", None)

        addr = self.repo.get_by_id(addr_id)
        if not addr:
            raise ValueError("ADDRESS_NOT_FOUND: Address does not exist")

        # G-12: correction allowed only when assignment is effective
        aa_repo = AddressAssignmentRepo(self.db)
        assignment = aa_repo.get_by_address_id(addr_id)
        if assignment is None:
            raise ValueError("ADDRESS_ASSIGNMENT_NOT_FOUND: correction requires an assigned address")
        today = date.today()
        is_effective = assignment.valid_from <= today and (assignment.valid_to is None or today <= assignment.valid_to)
        if not is_effective:
            raise ValueError("ADDRESS_NOT_EFFECTIVE: correction only allowed for effective addresses (valid_from <= today <= valid_to)")

        # Normalize text inputs — trim only, never truncate
        for key in ["address_line_1", "address_line_2", "locality", "landmark", "postal_code"]:
            if key in kwargs:
                kwargs[key] = _normalize_text(kwargs[key])

        # Field validation: required blanks -> ADDRESS_REQUIRED_FIELD, max lengths
        if "address_line_1" in kwargs:
            if not kwargs["address_line_1"]:
                raise ValueError("ADDRESS_REQUIRED_FIELD: address_line_1 is required")
            if len(kwargs["address_line_1"]) > 500:
                raise ValueError("ADDRESS_OVERLY_LONG: address_line_1 exceeds 500 characters")
        if "postal_code" in kwargs:
            if not kwargs["postal_code"]:
                raise ValueError("ADDRESS_REQUIRED_FIELD: postal_code is required")
            if len(kwargs["postal_code"]) > 20:
                raise ValueError("ADDRESS_OVERLY_LONG: postal_code exceeds 20 characters")
        if "address_line_2" in kwargs and kwargs["address_line_2"] is not None and len(kwargs["address_line_2"]) > 500:
            raise ValueError("ADDRESS_OVERLY_LONG: address_line_2 exceeds 500 characters")
        if "locality" in kwargs and kwargs["locality"] is not None and len(kwargs["locality"]) > 100:
            raise ValueError("ADDRESS_OVERLY_LONG: locality exceeds 100 characters")
        if "landmark" in kwargs and kwargs["landmark"] is not None and len(kwargs["landmark"]) > 100:
            raise ValueError("ADDRESS_OVERLY_LONG: landmark exceeds 100 characters")

        # Enforce geographic hierarchy if any geo field is being changed
        if any(k in kwargs for k in ("city_id", "state_id", "country_id")):
            effective_city_id = kwargs.get("city_id", addr.city_id)
            effective_state_id = kwargs.get("state_id", addr.state_id)
            effective_country_id = kwargs.get("country_id", addr.country_id)
            geo_repo = GeographicRepo(self.db)
            if not geo_repo.validate_hierarchy(effective_city_id, effective_state_id, effective_country_id):
                raise ValueError("GEOGRAPHIC_HIERARCHY_INVALID: City/State/Country hierarchy is invalid")

        # G-12: transactional correction with audit (before/after via AuditEmitter, rollback on failure)
        before = _address_snapshot(addr)
        try:
            updated = self.repo.update(addr, **kwargs)
            after = _address_snapshot(updated)
            # Resolve audit identifiers — use provided ctx or fallback to NIL UUID (emitter requires UUID)
            nil_uuid = uuid.UUID(int=0)
            audit_client_id = client_id if isinstance(client_id, uuid.UUID) else nil_uuid
            audit_institution_id = institution_id if isinstance(institution_id, uuid.UUID) else None
            # Default actor to system if not provided
            audit_actor = actor or "system"
            payload = {
                "address_id": str(addr.id),
                "assignment_id": str(assignment.id),
                "before": before,
                "after": after,
            }
            self._audit.emit(
                action="address.corrected",
                client_id=audit_client_id,
                institution_id=audit_institution_id,
                actor=audit_actor,
                payload=payload,
            )
            self.db.flush()
            return updated
        except Exception:
            self.db.rollback()
            raise

    def delete_address(self, addr: Address) -> None:
        """Delete an Address. G-10: Prohibit orphan-safe direct delete if still assigned.

        If an AddressAssignment still references this address, deletion must go
        through assignment ownership (delete assignment + address atomically).
        Callers should use AddressAssignmentService.delete_by_address_id or
        delete_assignment_and_address instead.
        """
        # G-10 guard: if still assigned, reject independent delete
        from kernel.address.repos import AddressAssignmentRepo as _AAR

        aar = _AAR(self.db)
        existing = aar.get_by_address_id(addr.id)
        if existing is not None:
            raise ValueError("ADDRESS_STILL_ASSIGNED: cannot delete Address independently while assigned; delete via assignment")
        self.repo.delete(addr)

    def replace_address(
        self,
        entity_type_id: uuid.UUID,
        entity_id: uuid.UUID,
        address_type_id: uuid.UUID,
        new_address_data: dict,
        valid_from: date,
    ) -> tuple[AddressAssignment, Address]:
        """G-09: Atomic replacement/move in one transaction.

        Steps (all in one transaction, rollback on failure):
          1) end old effective assignment: set valid_to = valid_from - 1 day
          2) create new Address row (never reuse)
          3) create new AddressAssignment with new valid_from

        Old Address stays historical and queryable.

        Args:
          entity_type_id, entity_id, address_type_id: identify the entity+type slot.
          new_address_data: dict with address_line_1, city_id, state_id, country_id,
                            optional address_line_2/locality/landmark/postal_code.
          valid_from: first day for the new assignment (must be > old valid_to).

        Returns (new_assignment, new_address). Raises ValueError with
        ADDRESS_* codes on validation failure; transaction rolls back.
        """
        aa_repo = AddressAssignmentRepo(self.db)
        # Determine effective assignment on day before valid_from that should be ended,
        # or today if valid_from is today. We look for any assignment that would
        # conflict or be the current effective one. Prefer the assignment that is
        # effective on (valid_from - 1 day) or currently effective.
        old_aa: AddressAssignment | None = None
        # Search for existing assignment for this entity+type that is effective
        # at valid_from - 1 day (the day we will set valid_to to).
        prev_day = valid_from - timedelta(days=1)
        # First try to find overlapping effective on prev_day
        candidates = aa_repo.get_effective(entity_type_id, entity_id, address_type_id, prev_day)
        if candidates is not None:
            old_aa = candidates
        else:
            # Also check for assignment effective today (handles gap or ongoing)
            # If multiple future, we still need to ensure no overlap for new period
            today = date.today()
            eff_today = aa_repo.get_effective(entity_type_id, entity_id, address_type_id, today)
            if eff_today is not None and (eff_today.valid_to is None or eff_today.valid_to >= prev_day):
                old_aa = eff_today

        # Validate new assignment would not overlap (excluding old which we will end)
        exclude_id = old_aa.id if old_aa else None
        if aa_repo.check_overlap(entity_type_id, entity_id, address_type_id, valid_from, None, exclude_id=exclude_id):
            raise ValueError("ADDRESS_ASSIGNMENT_OVERLAP: replacement valid_from overlaps existing assignment")

        # Validate valid_from ordering relative to old assignment if present
        if old_aa is not None:
            if valid_from <= old_aa.valid_from:
                raise ValueError("ADDRESS_ASSIGNMENT_DATE_INVALID: replacement valid_from must be after old valid_from")
            # If old has valid_to, new must be after it; otherwise we set it
            if old_aa.valid_to is not None and valid_from <= old_aa.valid_to:
                raise ValueError("ADDRESS_ASSIGNMENT_DATE_INVALID: replacement valid_from must be after old valid_to")

        try:
            # 1) End old assignment
            if old_aa is not None:
                new_valid_to = valid_from - timedelta(days=1)
                if new_valid_to < old_aa.valid_from:
                    raise ValueError("ADDRESS_ASSIGNMENT_DATE_INVALID: valid_to would be before valid_from")
                aa_repo.update(old_aa, valid_to=new_valid_to)

            # 2) Create new Address (never reuse) — validates hierarchy/fields internally
            new_addr = self.create_address(**new_address_data)

            # 3) Create new assignment (ownership + compatibility + overlap already checked)
            # Re-use AddressAssignmentService validation for compatibility
            type_repo = AddressTypeRepo(self.db)
            compatible_ids = type_repo.get_compatible_address_types(entity_type_id)
            if address_type_id not in compatible_ids:
                raise ValueError("ADDRESS_TYPE_NOT_COMPATIBLE: AddressType not compatible with EntityType")
            # Ownership check done by repo.create; also ensure no orphan reuse is already handled
            new_aa = aa_repo.create(
                entity_type_id=entity_type_id,
                entity_id=entity_id,
                address_id=new_addr.id,
                address_type_id=address_type_id,
                valid_from=valid_from,
                valid_to=None,
            )
            self.db.flush()
            return new_aa, new_addr
        except Exception:
            self.db.rollback()
            raise


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
        # G-08: valid_to inclusive, reject valid_to < valid_from, same-day allowed
        if valid_to is not None and valid_to < valid_from:
            raise ValueError("ADDRESS_ASSIGNMENT_DATE_INVALID: valid_to must be >= valid_from")
        # G-07: Address ownership exclusivity — app-level pre-check
        from sqlalchemy import select as _select

        from kernel.address.models.address_assignment import AddressAssignment as _AA

        _existing = self.db.execute(
            _select(_AA).where(_AA.address_id == address_id)
        ).scalar_one_or_none()
        if _existing is not None:
            raise ValueError("ADDRESS_ALREADY_ASSIGNED: Address is already assigned to an entity")

        # Validate address type compatibility
        compatible_ids = self.type_repo.get_compatible_address_types(entity_type_id)
        if address_type_id not in compatible_ids:
            raise ValueError("ADDRESS_TYPE_NOT_COMPATIBLE: AddressType not compatible with EntityType")

        # G-08: Check for overlapping assignments (inclusive valid_to, adjacent allowed,
        # one-effective per entity+type enforced via same check)
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

    def get_effective(
        self,
        entity_type_id: uuid.UUID,
        entity_id: uuid.UUID,
        address_type_id: uuid.UUID,
        on_date: date,
    ) -> AddressAssignment | None:
        """G-08: delegate to repo.get_effective for inclusive one-effective lookup."""
        return self.repo.get_effective(entity_type_id, entity_id, address_type_id, on_date)

    def get_by_address_id(self, address_id: uuid.UUID) -> AddressAssignment | None:
        return self.repo.get_by_address_id(address_id)

    def list_by_entity(
        self,
        entity_type_id: uuid.UUID,
        entity_id: uuid.UUID,
        effective_date: date | None = None,
    ) -> Sequence[AddressAssignment]:
        """List assignments; supports historical/current/future via valid_from/valid_to.

        When effective_date is provided, returns only effective on that date
        (valid_from <= date <= valid_to/null). Otherwise returns all (history+current+future).
        """
        return self.repo.list_by_entity(entity_type_id, entity_id, effective_date)

    def end_assignment(self, aa_id: uuid.UUID, end_date: date) -> AddressAssignment:
        """End an assignment by setting valid_to (inclusive)."""
        aa = self.repo.get_by_id(aa_id)
        if not aa:
            raise ValueError("ADDRESS_ASSIGNMENT_NOT_FOUND: AddressAssignment does not exist")
        if end_date < aa.valid_from:
            raise ValueError("ADDRESS_ASSIGNMENT_DATE_INVALID: valid_to must be >= valid_from")

        return self.repo.update(aa, valid_to=end_date)

    def delete_assignment_and_address(self, assignment_id: uuid.UUID) -> None:
        """G-10: Atomically delete assignment + owned Address (no orphan, rollback on failure)."""
        aa = self.repo.get_by_id(assignment_id)
        if not aa:
            raise ValueError("ADDRESS_ASSIGNMENT_NOT_FOUND: AddressAssignment does not exist")
        addr_repo = AddressRepo(self.db)
        addr = addr_repo.get_by_id(aa.address_id)
        try:
            self.repo.delete(aa)
            if addr is not None:
                addr_repo.delete(addr)
            self.db.flush()
        except Exception:
            self.db.rollback()
            raise

    def delete_by_address_id(self, address_id: uuid.UUID) -> None:
        """G-10: Delete via address_id — resolves assignment then deletes atomically."""
        aa = self.repo.get_by_address_id(address_id)
        if not aa:
            raise ValueError("ADDRESS_ASSIGNMENT_NOT_FOUND: no assignment for address")
        self.delete_assignment_and_address(aa.id)


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
        return self.repo.list_by_ids(compatible_ids)


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
