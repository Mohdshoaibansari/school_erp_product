"""C-06 Relationship Management — ContactRoleAssignmentService."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.relationship.models.contact_role_assignment import ContactRoleAssignment
from kernel.relationship.repos.contact_role_assignment_repo import ContactRoleAssignmentRepo
from kernel.relationship.repos.relationship_repo import RelationshipRepo
from kernel.relationship.services.contact_role_service import ContactRoleService


class ContactRoleAssignmentService:
    """Service for ContactRoleAssignment entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ContactRoleAssignmentRepo(db)
        self.rel_repo = RelationshipRepo(db)
        self.role_service = ContactRoleService(db)

    def add_role(
        self,
        client_id: uuid.UUID,
        relationship_id: uuid.UUID,
        contact_role_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None = None,
    ) -> ContactRoleAssignment:
        """Add a ContactRole to a Relationship with validation."""
        # Validate relationship exists
        rel = self.rel_repo.get_by_id(relationship_id)
        if not rel:
            raise ValueError("RELATIONSHIP_NOT_FOUND: Relationship does not exist")

        # Validate compatibility
        if not self.role_service.validate_compatibility(rel.relationship_type_id, contact_role_id):
            raise ValueError("CONTACT_ROLE_NOT_ALLOWED: ContactRole not compatible with RelationshipType")

        # Validate containment within relationship validity
        if valid_from < rel.valid_from:
            raise ValueError("CONTACT_ROLE_OUTSIDE_RELATIONSHIP: Role starts before relationship")

        if rel.valid_to and valid_to and valid_to > rel.valid_to:
            raise ValueError("CONTACT_ROLE_OUTSIDE_RELATIONSHIP: Role ends after relationship")

        if rel.valid_to and not valid_to:
            raise ValueError("CONTACT_ROLE_OUTSIDE_RELATIONSHIP: Relationship has end date but role does not")

        # Validate no overlap with same role
        if self.repo.check_overlap(relationship_id, contact_role_id, valid_from, valid_to):
            raise ValueError("CONTACT_ROLE_OVERLAP: Overlapping same-role period exists")

        return self.repo.create(
            client_id=client_id,
            relationship_id=relationship_id,
            contact_role_id=contact_role_id,
            valid_from=valid_from,
            valid_to=valid_to,
        )

    def get_by_id(self, cra_id: uuid.UUID) -> ContactRoleAssignment | None:
        return self.repo.get_by_id(cra_id)

    def list_by_relationship(
        self,
        relationship_id: uuid.UUID,
        effective_date: date | None = None,
    ) -> Sequence[ContactRoleAssignment]:
        return self.repo.list_by_relationship(relationship_id, effective_date)

    def update_role_period(
        self,
        cra_id: uuid.UUID,
        valid_from: date | None = None,
        valid_to: date | None = None,
    ) -> ContactRoleAssignment:
        """Update a ContactRoleAssignment period with validation."""
        cra = self.repo.get_by_id(cra_id)
        if not cra:
            raise ValueError("CONTACT_ROLE_NOT_FOUND: ContactRoleAssignment does not exist")

        rel = self.rel_repo.get_by_id(cra.relationship_id)
        if not rel:
            raise ValueError("RELATIONSHIP_NOT_FOUND: Relationship does not exist")

        new_from = valid_from or cra.valid_from
        new_to = valid_to if valid_to is not None else cra.valid_to

        # Validate containment
        if new_from < rel.valid_from:
            raise ValueError("CONTACT_ROLE_OUTSIDE_RELATIONSHIP: Role starts before relationship")

        if rel.valid_to and new_to and new_to > rel.valid_to:
            raise ValueError("CONTACT_ROLE_OUTSIDE_RELATIONSHIP: Role ends after relationship")

        # Validate no overlap (excluding self)
        if self.repo.check_overlap(cra.relationship_id, cra.contact_role_id, new_from, new_to, exclude_id=cra_id):
            raise ValueError("CONTACT_ROLE_OVERLAP: Overlapping same-role period exists")

        kwargs = {}
        if valid_from is not None:
            kwargs["valid_from"] = valid_from
        if valid_to is not None:
            kwargs["valid_to"] = valid_to

        return self.repo.update(cra, **kwargs)

    def end_role(self, cra_id: uuid.UUID, end_date: date) -> ContactRoleAssignment:
        """End a ContactRoleAssignment by setting valid_to."""
        cra = self.repo.get_by_id(cra_id)
        if not cra:
            raise ValueError("CONTACT_ROLE_NOT_FOUND: ContactRoleAssignment does not exist")

        return self.repo.update(cra, valid_to=end_date)
