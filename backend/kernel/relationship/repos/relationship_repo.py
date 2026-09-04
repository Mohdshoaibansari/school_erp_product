"""C-06 Relationship Management — Relationship repo."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from kernel.relationship.models.relationship import Relationship


class RelationshipRepo:
    """Repository for Relationship entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        person_a_id: uuid.UUID,
        person_b_id: uuid.UUID,
        relationship_type_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None,
        normalized_pair: str,
    ) -> Relationship:
        rel = Relationship(
            client_id=client_id,
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            relationship_type_id=relationship_type_id,
            valid_from=valid_from,
            valid_to=valid_to,
            normalized_pair=normalized_pair,
        )
        self.db.add(rel)
        self.db.flush()
        return rel

    def get_by_id(self, rel_id: uuid.UUID) -> Relationship | None:
        return self.db.get(Relationship, rel_id)

    def list_by_person(
        self,
        person_id: uuid.UUID,
        effective_date: date | None = None,
        relationship_type_id: uuid.UUID | None = None,
    ) -> Sequence[Relationship]:
        stmt = select(Relationship).where(
            or_(
                Relationship.person_a_id == person_id,
                Relationship.person_b_id == person_id,
            )
        )

        if effective_date:
            stmt = stmt.where(
                and_(
                    Relationship.valid_from <= effective_date,
                    or_(
                        Relationship.valid_to.is_(None),
                        Relationship.valid_to >= effective_date,
                    ),
                )
            )

        if relationship_type_id:
            stmt = stmt.where(Relationship.relationship_type_id == relationship_type_id)

        stmt = stmt.order_by(Relationship.valid_from.desc())
        return list(self.db.execute(stmt).scalars().all())

    def check_overlap(
        self,
        normalized_pair: str,
        valid_from: date,
        valid_to: date | None,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if overlapping relationship exists for the same person pair."""
        stmt = select(Relationship).where(
            Relationship.normalized_pair == normalized_pair,
        )

        if exclude_id:
            stmt = stmt.where(Relationship.id != exclude_id)

        # Check for temporal overlap
        if valid_to:
            stmt = stmt.where(
                and_(
                    Relationship.valid_from <= valid_to,
                    or_(
                        Relationship.valid_to.is_(None),
                        Relationship.valid_to >= valid_from,
                    ),
                )
            )
        else:
            # valid_to is NULL (ongoing) - overlaps with anything that starts after valid_from
            stmt = stmt.where(
                or_(
                    Relationship.valid_to.is_(None),
                    Relationship.valid_to >= valid_from,
                )
            )

        return self.db.execute(stmt).scalar_one_or_none() is not None

    def update(self, rel: Relationship, **kwargs) -> Relationship:
        for key, value in kwargs.items():
            setattr(rel, key, value)
        self.db.flush()
        return rel
