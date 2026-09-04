"""C-06 Relationship Management — ContactRole repo."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.relationship.models.contact_role import ContactRole


class ContactRoleRepo:
    """Repository for ContactRole entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        code: str,
        name: str,
    ) -> ContactRole:
        cr = ContactRole(
            client_id=client_id,
            code=code,
            name=name,
        )
        self.db.add(cr)
        self.db.flush()
        return cr

    def get_by_id(self, cr_id: uuid.UUID) -> ContactRole | None:
        return self.db.get(ContactRole, cr_id)

    def get_by_code(self, code: str) -> ContactRole | None:
        stmt = select(ContactRole).where(ContactRole.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> Sequence[ContactRole]:
        stmt = select(ContactRole).order_by(ContactRole.name)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_ids(self, ids: list[uuid.UUID]) -> Sequence[ContactRole]:
        stmt = select(ContactRole).where(ContactRole.id.in_(ids))
        return list(self.db.execute(stmt).scalars().all())
