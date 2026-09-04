"""C-06 Relationship Management — Tests.

Tests for:
- Relationship CRUD and temporal validation
- Symmetric normalization
- ContactRole compatibility and containment
- RelationshipType change validation
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from kernel.relationship.models.relationship_type import RelationshipType
from kernel.relationship.models.contact_role import ContactRole
from kernel.relationship.models.relationship import Relationship
from kernel.relationship.models.contact_role_assignment import ContactRoleAssignment

from kernel.relationship.repos.relationship_type_repo import RelationshipTypeRepo
from kernel.relationship.repos.contact_role_repo import ContactRoleRepo
from kernel.relationship.repos.relationship_repo import RelationshipRepo
from kernel.relationship.repos.contact_role_assignment_repo import ContactRoleAssignmentRepo

from kernel.relationship.services.relationship_type_service import RelationshipTypeService
from kernel.relationship.services.contact_role_service import ContactRoleService
from kernel.relationship.services.relationship_service import RelationshipService
from kernel.relationship.services.contact_role_assignment_service import ContactRoleAssignmentService


# ============================================================
# Test Relationship CRUD
# ============================================================

class TestRelationshipCRUD:
    """Tests for Relationship CRUD operations."""

    def test_create_relationship(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test creating a valid Relationship."""
        # Create relationship type
        type_repo = RelationshipTypeRepo(db)
        rt = type_repo.create(test_client_id, "mother", "Mother", is_symmetric=False)

        # Create relationship
        rel_repo = RelationshipRepo(db)
        normalized_pair = f"{min(test_person_a_id, test_person_b_id)}{max(test_person_a_id, test_person_b_id)}"
        rel = rel_repo.create(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt.id,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            normalized_pair=normalized_pair,
        )

        assert rel.person_a_id == test_person_a_id
        assert rel.person_b_id == test_person_b_id
        assert rel.valid_to is None

    def test_reject_self_relationship(self, db: Session, test_client_id, test_person_a_id):
        """Test that self-relationships are rejected."""
        type_repo = RelationshipTypeRepo(db)
        rt = type_repo.create(test_client_id, "mother", "Mother")

        svc = RelationshipService(db)
        with pytest.raises(ValueError, match="SELF_RELATIONSHIP_NOT_ALLOWED"):
            svc.create_relationship(
                client_id=test_client_id,
                person_a_id=test_person_a_id,
                person_b_id=test_person_a_id,
                relationship_type_id=rt.id,
                valid_from=date(2026, 1, 1),
            )

    def test_reject_overlapping_relationship(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test that overlapping relationships are rejected."""
        type_repo = RelationshipTypeRepo(db)
        rt = type_repo.create(test_client_id, "mother", "Mother")

        svc = RelationshipService(db)

        # Create first relationship
        svc.create_relationship(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt.id,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 12, 31),
        )

        # Try overlapping relationship
        with pytest.raises(ValueError, match="RELATIONSHIP_OVERLAP"):
            svc.create_relationship(
                client_id=test_client_id,
                person_a_id=test_person_a_id,
                person_b_id=test_person_b_id,
                relationship_type_id=rt.id,
                valid_from=date(2026, 6, 1),
                valid_to=None,
            )

    def test_non_overlapping_relationships_allowed(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test that non-overlapping relationships are allowed."""
        type_repo = RelationshipTypeRepo(db)
        rt = type_repo.create(test_client_id, "mother", "Mother")

        svc = RelationshipService(db)

        # Create first relationship
        svc.create_relationship(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt.id,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 6, 30),
        )

        # Create non-overlapping relationship
        rel2 = svc.create_relationship(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt.id,
            valid_from=date(2026, 7, 1),
            valid_to=None,
        )

        assert rel2 is not None


# ============================================================
# Test Symmetric Normalization
# ============================================================

class TestSymmetricNormalization:
    """Tests for symmetric relationship normalization."""

    def test_symmetric_normalization(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test that symmetric relationships normalize person IDs."""
        type_repo = RelationshipTypeRepo(db)
        rt = type_repo.create(test_client_id, "sibling", "Sibling", is_symmetric=True)

        svc = RelationshipService(db)

        # Create relationship with person_b first
        rel = svc.create_relationship(
            client_id=test_client_id,
            person_a_id=test_person_b_id,
            person_b_id=test_person_a_id,
            relationship_type_id=rt.id,
            valid_from=date(2026, 1, 1),
        )

        # Verify normalization (person_a_id should be the smaller UUID)
        assert rel.person_a_id == min(test_person_a_id, test_person_b_id)
        assert rel.person_b_id == max(test_person_a_id, test_person_b_id)


# ============================================================
# Test ContactRole Compatibility
# ============================================================

class TestContactRoleCompatibility:
    """Tests for ContactRole compatibility validation."""

    def test_compatible_role_allowed(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test that compatible roles are allowed."""
        type_repo = RelationshipTypeRepo(db)
        role_repo = ContactRoleRepo(db)

        # Create type and role
        rt = type_repo.create(test_client_id, "mother", "Mother")
        cr = role_repo.create(test_client_id, "guardian", "Guardian")

        # Add compatibility
        type_repo.add_compatibility(rt.id, cr.id)

        # Create relationship
        rel_repo = RelationshipRepo(db)
        normalized_pair = f"{min(test_person_a_id, test_person_b_id)}{max(test_person_a_id, test_person_b_id)}"
        rel = rel_repo.create(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt.id,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            normalized_pair=normalized_pair,
        )

        # Add compatible role
        cra_svc = ContactRoleAssignmentService(db)
        cra = cra_svc.add_role(
            client_id=test_client_id,
            relationship_id=rel.id,
            contact_role_id=cr.id,
            valid_from=date(2026, 1, 1),
        )

        assert cra is not None

    def test_incompatible_role_rejected(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test that incompatible roles are rejected."""
        type_repo = RelationshipTypeRepo(db)
        role_repo = ContactRoleRepo(db)

        # Create type and role (no compatibility added)
        rt = type_repo.create(test_client_id, "mother", "Mother")
        cr = role_repo.create(test_client_id, "guardian", "Guardian")

        # Create relationship
        rel_repo = RelationshipRepo(db)
        normalized_pair = f"{min(test_person_a_id, test_person_b_id)}{max(test_person_a_id, test_person_b_id)}"
        rel = rel_repo.create(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt.id,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            normalized_pair=normalized_pair,
        )

        # Try to add incompatible role
        cra_svc = ContactRoleAssignmentService(db)
        with pytest.raises(ValueError, match="CONTACT_ROLE_NOT_ALLOWED"):
            cra_svc.add_role(
                client_id=test_client_id,
                relationship_id=rel.id,
                contact_role_id=cr.id,
                valid_from=date(2026, 1, 1),
            )


# ============================================================
# Test Containment
# ============================================================

class TestContainment:
    """Tests for role containment within relationship validity."""

    def test_role_outside_relationship_rejected(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test that roles outside relationship validity are rejected."""
        type_repo = RelationshipTypeRepo(db)
        role_repo = ContactRoleRepo(db)

        # Create type and role
        rt = type_repo.create(test_client_id, "mother", "Mother")
        cr = role_repo.create(test_client_id, "guardian", "Guardian")
        type_repo.add_compatibility(rt.id, cr.id)

        # Create relationship
        rel_repo = RelationshipRepo(db)
        normalized_pair = f"{min(test_person_a_id, test_person_b_id)}{max(test_person_a_id, test_person_b_id)}"
        rel = rel_repo.create(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt.id,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 12, 31),
            normalized_pair=normalized_pair,
        )

        # Try to add role outside relationship validity
        cra_svc = ContactRoleAssignmentService(db)
        with pytest.raises(ValueError, match="CONTACT_ROLE_OUTSIDE_RELATIONSHIP"):
            cra_svc.add_role(
                client_id=test_client_id,
                relationship_id=rel.id,
                contact_role_id=cr.id,
                valid_from=date(2026, 1, 1),
                valid_to=date(2027, 6, 30),  # Extends beyond relationship
            )


# ============================================================
# Test RelationshipType Change
# ============================================================

class TestRelationshipTypeChange:
    """Tests for RelationshipType change validation."""

    def test_type_change_with_compatible_roles(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test that type change is allowed when all roles are compatible."""
        type_repo = RelationshipTypeRepo(db)
        role_repo = ContactRoleRepo(db)

        # Create types
        rt1 = type_repo.create(test_client_id, "mother", "Mother")
        rt2 = type_repo.create(test_client_id, "guardian", "Guardian")

        # Create role compatible with both
        cr = role_repo.create(test_client_id, "primary_guardian", "Primary Guardian")
        type_repo.add_compatibility(rt1.id, cr.id)
        type_repo.add_compatibility(rt2.id, cr.id)

        # Create relationship with role
        rel_repo = RelationshipRepo(db)
        normalized_pair = f"{min(test_person_a_id, test_person_b_id)}{max(test_person_a_id, test_person_b_id)}"
        rel = rel_repo.create(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt1.id,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            normalized_pair=normalized_pair,
        )

        cra_repo = ContactRoleAssignmentRepo(db)
        cra_repo.create(test_client_id, rel.id, cr.id, date(2026, 1, 1), None)

        # Change type - should succeed
        svc = RelationshipService(db)
        updated = svc.update_relationship(rel.id, relationship_type_id=rt2.id)
        assert updated.relationship_type_id == rt2.id

    def test_type_change_with_incompatible_roles_rejected(self, db: Session, test_client_id, test_person_a_id, test_person_b_id):
        """Test that type change is rejected when roles are incompatible."""
        type_repo = RelationshipTypeRepo(db)
        role_repo = ContactRoleRepo(db)

        # Create types
        rt1 = type_repo.create(test_client_id, "mother", "Mother")
        rt2 = type_repo.create(test_client_id, "sibling", "Sibling", is_symmetric=True)

        # Create role compatible only with rt1
        cr = role_repo.create(test_client_id, "primary_guardian", "Primary Guardian")
        type_repo.add_compatibility(rt1.id, cr.id)
        # Not compatible with rt2

        # Create relationship with role
        rel_repo = RelationshipRepo(db)
        normalized_pair = f"{min(test_person_a_id, test_person_b_id)}{max(test_person_a_id, test_person_b_id)}"
        rel = rel_repo.create(
            client_id=test_client_id,
            person_a_id=test_person_a_id,
            person_b_id=test_person_b_id,
            relationship_type_id=rt1.id,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            normalized_pair=normalized_pair,
        )

        cra_repo = ContactRoleAssignmentRepo(db)
        cra_repo.create(test_client_id, rel.id, cr.id, date(2026, 1, 1), None)

        # Change type - should fail
        svc = RelationshipService(db)
        with pytest.raises(ValueError, match="RELATIONSHIP_TYPE_CHANGE_REQUIRES_RECONCILIATION"):
            svc.update_relationship(rel.id, relationship_type_id=rt2.id)


# ============================================================
# Test RelationshipType Inverse Pair
# ============================================================

class TestRelationshipTypeInverse:
    """Tests for RelationshipType inverse pair creation."""

    def test_auto_generate_inverse(self, db: Session, test_client_id):
        """Test that non-symmetric types auto-generate inverse."""
        svc = RelationshipTypeService(db)

        # Create non-symmetric type
        mother = svc.create_relationship_type(
            client_id=test_client_id,
            code="mother",
            name="Mother",
            is_symmetric=False,
        )

        # Verify inverse was created
        assert mother.inverse_relationship_type_id is not None

        child = svc.get_by_id(mother.inverse_relationship_type_id)
        assert child is not None
        assert child.code == "child"
        assert child.inverse_relationship_type_id == mother.id

    def test_symmetric_no_inverse(self, db: Session, test_client_id):
        """Test that symmetric types don't have inverse."""
        svc = RelationshipTypeService(db)

        sibling = svc.create_relationship_type(
            client_id=test_client_id,
            code="sibling",
            name="Sibling",
            is_symmetric=True,
        )

        assert sibling.inverse_relationship_type_id is None


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def test_client_id():
    return uuid.uuid4()


@pytest.fixture
def test_person_a_id():
    return uuid.uuid4()


@pytest.fixture
def test_person_b_id():
    return uuid.uuid4()


@pytest.fixture
def db():
    """Mock DB session for unit tests."""
    from unittest.mock import MagicMock
    return MagicMock(spec=Session)
