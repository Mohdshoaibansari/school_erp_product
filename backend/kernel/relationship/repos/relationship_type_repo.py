"""C-06 Relationship Management — RelationshipType repo."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.relationship.models.relationship_type import RelationshipType
from kernel.relationship.models.relationship_type_contact_role import RelationshipTypeContactRole


class RelationshipTypeRepo:
    """Repository for RelationshipType entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        code: str,
        name: str,
        inverse_relationship_type_id: uuid.UUID | None = None,
        is_symmetric: bool = False,
    ) -> RelationshipType:
        rt = RelationshipType(
            client_id=client_id,
            code=code,
            name=name,
            inverse_relationship_type_id=inverse_relationship_type_id,
            is_symmetric=is_symmetric,
        )
        self.db.add(rt)
        self.db.flush()
        return rt

    def get_by_id(self, rt_id: uuid.UUID) -> RelationshipType | None:
        return self.db.get(RelationshipType, rt_id)

    def get_by_code(self, code: str) -> RelationshipType | None:
        stmt = select(RelationshipType).where(RelationshipType.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> Sequence[RelationshipType]:
        stmt = select(RelationshipType).order_by(RelationshipType.name)
        return list(self.db.execute(stmt).scalars().all())

    def add_compatibility(self, relationship_type_id: uuid.UUID, contact_role_id: uuid.UUID) -> RelationshipTypeContactRole:
        compat = RelationshipTypeContactRole(
            relationship_type_id=relationship_type_id,
            contact_role_id=contact_role_id,
        )
        self.db.add(compat)
        self.db.flush()
        return compat

    def get_compatible_roles(self, relationship_type_id: uuid.UUID) -> Sequence[uuid.UUID]:
        stmt = select(RelationshipTypeContactRole.contact_role_id).where(
            RelationshipTypeContactRole.relationship_type_id == relationship_type_id
        )
        return list(self.db.execute(stmt).scalars().all())
