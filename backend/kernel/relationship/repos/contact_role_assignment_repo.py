"""C-06 Relationship Management — ContactRoleAssignment repo."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from kernel.relationship.models.contact_role_assignment import ContactRoleAssignment


class ContactRoleAssignmentRepo:
    """Repository for ContactRoleAssignment entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        relationship_id: uuid.UUID,
        contact_role_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None,
    ) -> ContactRoleAssignment:
        cra = ContactRoleAssignment(
            client_id=client_id,
            relationship_id=relationship_id,
            contact_role_id=contact_role_id,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        self.db.add(cra)
        self.db.flush()
        return cra

    def get_by_id(self, cra_id: uuid.UUID) -> ContactRoleAssignment | None:
        return self.db.get(ContactRoleAssignment, cra_id)

    def list_by_relationship(
        self,
        relationship_id: uuid.UUID,
        effective_date: date | None = None,
    ) -> Sequence[ContactRoleAssignment]:
        stmt = select(ContactRoleAssignment).where(
            ContactRoleAssignment.relationship_id == relationship_id
        )

        if effective_date:
            stmt = stmt.where(
                and_(
                    ContactRoleAssignment.valid_from <= effective_date,
                    or_(
                        ContactRoleAssignment.valid_to.is_(None),
                        ContactRoleAssignment.valid_to >= effective_date,
                    ),
                )
            )

        return list(self.db.execute(stmt).scalars().all())

    def check_overlap(
        self,
        relationship_id: uuid.UUID,
        contact_role_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if overlapping same-role period exists for the same relationship."""
        stmt = select(ContactRoleAssignment).where(
            ContactRoleAssignment.relationship_id == relationship_id,
            ContactRoleAssignment.contact_role_id == contact_role_id,
        )

        if exclude_id:
            stmt = stmt.where(ContactRoleAssignment.id != exclude_id)

        # Check for temporal overlap
        if valid_to:
            stmt = stmt.where(
                and_(
                    ContactRoleAssignment.valid_from <= valid_to,
                    or_(
                        ContactRoleAssignment.valid_to.is_(None),
                        ContactRoleAssignment.valid_to >= valid_from,
                    ),
                )
            )
        else:
            stmt = stmt.where(
                or_(
                    ContactRoleAssignment.valid_to.is_(None),
                    ContactRoleAssignment.valid_to >= valid_from,
                )
            )

        return self.db.execute(stmt).scalar_one_or_none() is not None

    def update(self, cra: ContactRoleAssignment, **kwargs) -> ContactRoleAssignment:
        for key, value in kwargs.items():
            setattr(cra, key, value)
        self.db.flush()
        return cra
