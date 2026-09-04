"""C-06 Relationship Management — RelationshipService."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.relationship.models.relationship import Relationship
from kernel.relationship.repos.relationship_repo import RelationshipRepo
from kernel.relationship.repos.relationship_type_repo import RelationshipTypeRepo
from kernel.relationship.services.contact_role_service import ContactRoleService


class RelationshipService:
    """Service for Relationship entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = RelationshipRepo(db)
        self.type_repo = RelationshipTypeRepo(db)
        self.role_service = ContactRoleService(db)

    def create_relationship(
        self,
        client_id: uuid.UUID,
        person_a_id: uuid.UUID,
        person_b_id: uuid.UUID,
        relationship_type_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None = None,
    ) -> Relationship:
        """Create a Relationship with validation."""
        # Validate persons are different
        if person_a_id == person_b_id:
            raise ValueError("SELF_RELATIONSHIP_NOT_ALLOWED: Cannot relate person to themselves")

        # Validate relationship type exists
        rel_type = self.type_repo.get_by_id(relationship_type_id)
        if not rel_type:
            raise ValueError("RELATIONSHIP_TYPE_NOT_FOUND: RelationshipType does not exist")

        # Normalize for symmetric relationships
        if rel_type.is_symmetric:
            norm_a = min(person_a_id, person_b_id)
            norm_b = max(person_a_id, person_b_id)
        else:
            norm_a = person_a_id
            norm_b = person_b_id

        normalized_pair = f"{norm_a}{norm_b}"

        # Check for overlapping relationships
        if self.repo.check_overlap(normalized_pair, valid_from, valid_to):
            raise ValueError("RELATIONSHIP_OVERLAP: Overlapping relationship exists for this person pair")

        return self.repo.create(
            client_id=client_id,
            person_a_id=norm_a,
            person_b_id=norm_b,
            relationship_type_id=relationship_type_id,
            valid_from=valid_from,
            valid_to=valid_to,
            normalized_pair=normalized_pair,
        )

    def get_by_id(self, rel_id: uuid.UUID) -> Relationship | None:
        return self.repo.get_by_id(rel_id)

    def list_by_person(
        self,
        person_id: uuid.UUID,
        effective_date: date | None = None,
        relationship_type_id: uuid.UUID | None = None,
    ) -> Sequence[Relationship]:
        return self.repo.list_by_person(person_id, effective_date, relationship_type_id)

    def update_relationship(
        self,
        rel_id: uuid.UUID,
        valid_from: date | None = None,
        valid_to: date | None = None,
        relationship_type_id: uuid.UUID | None = None,
    ) -> Relationship:
        """Update a Relationship with validation."""
        rel = self.repo.get_by_id(rel_id)
        if not rel:
            raise ValueError("RELATIONSHIP_NOT_FOUND: Relationship does not exist")

        # If changing dates, validate no role falls outside
        if valid_from is not None or valid_to is not None:
            new_from = valid_from or rel.valid_from
            new_to = valid_to if valid_to is not None else rel.valid_to
            self._validate_date_change(rel, new_from, new_to)

        # If changing type, validate compatibility
        if relationship_type_id is not None and relationship_type_id != rel.relationship_type_id:
            self._validate_type_change(rel, relationship_type_id)

        kwargs = {}
        if valid_from is not None:
            kwargs["valid_from"] = valid_from
        if valid_to is not None:
            kwargs["valid_to"] = valid_to
        if relationship_type_id is not None:
            kwargs["relationship_type_id"] = relationship_type_id

        return self.repo.update(rel, **kwargs)

    def end_relationship(self, rel_id: uuid.UUID, end_date: date) -> Relationship:
        """End a Relationship by setting valid_to."""
        rel = self.repo.get_by_id(rel_id)
        if not rel:
            raise ValueError("RELATIONSHIP_NOT_FOUND: Relationship does not exist")

        # Validate no role extends beyond end_date
        self._validate_date_change(rel, rel.valid_from, end_date)

        return self.repo.update(rel, valid_to=end_date)

    def _validate_date_change(self, rel: Relationship, new_from: date, new_to: date | None) -> None:
        """Validate that date changes don't invalidate existing roles."""
        from kernel.relationship.repos.contact_role_assignment_repo import ContactRoleAssignmentRepo
        cra_repo = ContactRoleAssignmentRepo(self.db)

        roles = cra_repo.list_by_relationship(rel.id)
        for role in roles:
            if role.valid_from < new_from:
                raise ValueError(
                    "RELATIONSHIP_TYPE_CHANGE_REQUIRES_RECONCILIATION: "
                    f"Role {role.id} starts before new relationship start date"
                )
            if new_to and role.valid_to and role.valid_to > new_to:
                raise ValueError(
                    "RELATIONSHIP_TYPE_CHANGE_REQUIRES_RECONCILIATION: "
                    f"Role {role.id} ends after new relationship end date"
                )

    def _validate_type_change(self, rel: Relationship, new_type_id: uuid.UUID) -> None:
        """Validate that type change doesn't invalidate existing roles."""
        from kernel.relationship.repos.contact_role_assignment_repo import ContactRoleAssignmentRepo
        cra_repo = ContactRoleAssignmentRepo(self.db)

        roles = cra_repo.list_by_relationship(rel.id)
        for role in roles:
            if not self.role_service.validate_compatibility(new_type_id, role.contact_role_id):
                raise ValueError(
                    "RELATIONSHIP_TYPE_CHANGE_REQUIRES_RECONCILIATION: "
                    f"Role {role.id} is incompatible with new relationship type"
                )
