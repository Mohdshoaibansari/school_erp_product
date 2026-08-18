"""PersonRepository (T-14).

Repository for the Person entity (D3a — enduring human anchor).
Inherits TenantAwareRepositoryBase[Person]. Methods: create, get, get_by_id_unscoped, update.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.user.models.person import Person
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.user.services.dtos import PersonCreateDTO, PersonDTO


class PersonRepository(TenantAwareRepositoryBase[Person]):
    """Repository for the Person entity (D3a).

    Auto-injects client_id from TenantContext. Returns PersonDTO.
    """

    def __init__(self) -> None:
        super().__init__(Person)

    def _to_dto(self, obj: Person) -> PersonDTO:
        return PersonDTO.model_validate(obj)

    def create(self, session: Session, ctx: TenantContext, dto: PersonCreateDTO) -> PersonDTO:
        """Insert a person row with an independent UUID (D3a, D3f).

        person.id is independent of any account UUID.
        """
        person_id = uuid.uuid4()
        obj = Person(
            id=person_id,
            client_id=ctx.client_id,
            name=dto.name,
            date_of_birth=dto.date_of_birth,
            gender=dto.gender,
            blood_group=dto.blood_group,
            photo=dto.photo,
            contact_phone=dto.contact_phone,
            contact_email=dto.contact_email,
            demographics=dto.demographics,
            status="Active",
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def get(self, session: Session, ctx: TenantContext, person_id: uuid.UUID) -> PersonDTO | None:
        """Get a person by ID, tenant-filtered."""
        stmt = select(Person).where(Person.id == person_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def get_by_id_unscoped(self, session: Session, person_id: uuid.UUID) -> PersonDTO | None:
        """Get a person by ID, bypassing tenant filter (for internal lookups)."""
        stmt = select(Person).where(Person.id == person_id)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def update(self, session: Session, ctx: TenantContext, person_id: uuid.UUID, data: dict) -> PersonDTO:
        """Update person human data."""
        stmt = select(Person).where(Person.id == person_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Person not found")

        for key, value in data.items():
            if hasattr(obj, key) and value is not None:
                setattr(obj, key, value)
        session.flush()
        return self._to_dto(obj)
