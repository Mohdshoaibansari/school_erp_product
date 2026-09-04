"""C-06 Relationship Management — RelationshipTypeService."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.relationship.models.relationship_type import RelationshipType
from kernel.relationship.repos.relationship_type_repo import RelationshipTypeRepo


class RelationshipTypeService:
    """Service for RelationshipType entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = RelationshipTypeRepo(db)

    def create_relationship_type(
        self,
        client_id: uuid.UUID,
        code: str,
        name: str,
        is_symmetric: bool = False,
    ) -> RelationshipType:
        """Create a RelationshipType. For non-symmetric types, auto-generates the inverse."""
        # Check if code already exists
        existing = self.repo.get_by_code(code)
        if existing:
            raise ValueError(f"RelationshipType with code '{code}' already exists")

        if is_symmetric:
            # Symmetric type - no inverse needed
            return self.repo.create(
                client_id=client_id,
                code=code,
                name=name,
                is_symmetric=True,
            )
        else:
            # Non-symmetric - create pair transactionally
            # Create the primary type first (without inverse)
            primary = self.repo.create(
                client_id=client_id,
                code=code,
                name=name,
                is_symmetric=False,
            )

            # Create the inverse type
            inverse_code = self._generate_inverse_code(code)
            inverse_name = self._generate_inverse_name(name)
            inverse = self.repo.create(
                client_id=client_id,
                code=inverse_code,
                name=inverse_name,
                is_symmetric=False,
            )

            # Link them
            primary.inverse_relationship_type_id = inverse.id
            inverse.inverse_relationship_type_id = primary.id
            self.db.flush()

            return primary

    def get_by_id(self, rt_id: uuid.UUID) -> RelationshipType | None:
        return self.repo.get_by_id(rt_id)

    def list_all(self) -> Sequence[RelationshipType]:
        return self.repo.list_all()

    def _generate_inverse_code(self, code: str) -> str:
        """Generate inverse code (e.g., 'mother' -> 'child')."""
        inverse_map = {
            "mother": "child",
            "father": "child",
            "guardian": "child",
            "grandparent": "grandchild",
            "foster_parent": "foster_child",
            "step_parent": "step_child",
        }
        return inverse_map.get(code, f"{code}_inverse")

    def _generate_inverse_name(self, name: str) -> str:
        """Generate inverse name (e.g., 'Mother' -> 'Child')."""
        inverse_map = {
            "Mother": "Child",
            "Father": "Child",
            "Guardian": "Child",
            "Grandparent": "Grandchild",
            "Foster Parent": "Foster Child",
            "Step Parent": "Step Child",
        }
        return inverse_map.get(name, f"{name} (Inverse)")
