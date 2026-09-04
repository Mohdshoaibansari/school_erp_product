"""C-06 Relationship Management — ContactRoleService."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.relationship.models.contact_role import ContactRole
from kernel.relationship.repos.contact_role_repo import ContactRoleRepo
from kernel.relationship.repos.relationship_type_repo import RelationshipTypeRepo


class ContactRoleService:
    """Service for ContactRole entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ContactRoleRepo(db)
        self.type_repo = RelationshipTypeRepo(db)

    def list_all(self) -> Sequence[ContactRole]:
        return self.repo.list_all()

    def list_compatible_roles(self, relationship_type_id: uuid.UUID) -> Sequence[ContactRole]:
        """List ContactRoles compatible with a RelationshipType."""
        compatible_ids = self.type_repo.get_compatible_roles(relationship_type_id)
        if not compatible_ids:
            return []
        return self.repo.list_by_ids(compatible_ids)

    def validate_compatibility(
        self,
        relationship_type_id: uuid.UUID,
        contact_role_id: uuid.UUID,
    ) -> bool:
        """Validate that a ContactRole is compatible with a RelationshipType."""
        compatible_ids = self.type_repo.get_compatible_roles(relationship_type_id)
        return contact_role_id in compatible_ids
