"""ClientUserRepository (task 3.3, T-16 modified).

Person-first insert order (D3a, D3f): person → user_account → client_user.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from kernel.tenant_context import TenantContext
from kernel.user.models.client_user import ClientUser
from kernel.user.models.client_user_lifecycle_event import ClientUserLifecycleEvent
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.user.services.dtos import ClientUserDTO, ClientUserCreateDTO, ClientUserUpdateDTO, PersonDTO


class ClientUserRepository(TenantAwareRepositoryBase[ClientUser]):
    """Repository for the ClientUser entity (D1, D3, D10, D6a).

    Person-first insert order: person → user_account → client_user.
    """

    def __init__(self, person_repo=None) -> None:
        super().__init__(ClientUser)
        self._person_repo = person_repo

    def _get_person_repo(self):
        if self._person_repo is None:
            from kernel.user.repos.person_repo import PersonRepository
            self._person_repo = PersonRepository()
        return self._person_repo

    def _to_dto(self, obj: ClientUser) -> ClientUserDTO:
        """Convert ORM ClientUser to ClientUserDTO with person projection."""
        person_dto = None
        if obj.person is not None:
            person_dto = PersonDTO.model_validate(obj.person)
        else:
            person_dto = PersonDTO(
                id=obj.person_id or uuid.UUID(int=0),
                client_id=obj.client_id,
                name="Unknown",
                status="Active",
                created_at=obj.created_at,
                updated_at=obj.updated_at,
            )
        return ClientUserDTO(
            id=obj.id,
            client_id=obj.client_id,
            email=obj.email,
            person=person_dto,
            role_id=obj.role_id,
            lifecycle_status=obj.lifecycle_status,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    def _load_with_person(self, session: Session, user_id: uuid.UUID) -> ClientUser | None:
        """Load client_user with eagerly loaded person relationship."""
        return session.execute(
            select(ClientUser)
            .options(joinedload(ClientUser.person))
            .where(ClientUser.id == user_id)
        ).scalars().first()

    def create(
        self, session: Session, ctx: TenantContext, dto: ClientUserCreateDTO,
        *,
        user_id: uuid.UUID | None = None,
    ) -> ClientUserDTO:
        """Create a new ClientUser with person-first insert order (D3a)."""
        existing = session.execute(
            select(ClientUser).where(ClientUser.email == dto.email)
        ).scalars().first()
        if existing:
            raise ValueError(f"Email '{dto.email}' is already taken in client_user")

        uid = user_id or uuid.uuid4()
        client_id = ctx.client_id or dto.client_id

        # 1. Insert person first (independent UUID, D3a)
        person_repo = self._get_person_repo()
        person_dto = person_repo.create(session, ctx, dto.person_data)

        # 2. D12: Insert user_account parent row
        from sqlalchemy import text as sa_text
        session.execute(sa_text(
            "INSERT INTO user_account (id) VALUES (:id) ON CONFLICT (id) DO NOTHING"
        ), {"id": uid})

        # 3. Insert client_user with person_id (no name, no user_category_id)
        obj = ClientUser(
            id=uid,
            client_id=client_id,
            email=dto.email,
            person_id=person_dto.id,
            role_id=dto.role_id,
            lifecycle_status="invited",
        )
        session.add(obj)
        session.flush()

        # Reload with person
        obj = self._load_with_person(session, uid)
        return self._to_dto(obj)

    def get_by_id(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
    ) -> ClientUserDTO | None:
        """Get a ClientUser by ID with person projection."""
        stmt = select(ClientUser).options(joinedload(ClientUser.person)).where(ClientUser.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def get_by_email(
        self, session: Session, email: str,
    ) -> ClientUserDTO | None:
        """Get a ClientUser by email (not tenant-filtered — email is globally unique)."""
        stmt = select(ClientUser).options(joinedload(ClientUser.person)).where(ClientUser.email == email)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def list_by_client(
        self, session: Session, ctx: TenantContext, client_id: uuid.UUID,
    ) -> list[ClientUserDTO]:
        """List all ClientUsers for a given client."""
        stmt = select(ClientUser).options(joinedload(ClientUser.person)).where(ClientUser.client_id == client_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        objs = session.execute(stmt).scalars().unique().all()
        return [self._to_dto(obj) for obj in objs]

    def update(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
        dto: ClientUserUpdateDTO,
    ) -> ClientUserDTO:
        """Update ClientUser fields. Name updates route to person (REQ-CUB-04)."""
        stmt = select(ClientUser).options(joinedload(ClientUser.person)).where(ClientUser.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("ClientUser not found")

        data = dto.model_dump(exclude_unset=True)

        # Route name to person (REQ-CUB-04)
        if "name" in data and data["name"] is not None:
            person_repo = self._get_person_repo()
            person_repo.update(session, ctx, obj.person_id, {"name": data.pop("name")})

        if "email" in data and data["email"] != obj.email:
            existing = session.execute(
                select(ClientUser).where(
                    ClientUser.email == data["email"],
                    ClientUser.id != user_id
                )
            ).scalars().first()
            if existing:
                raise ValueError(f"Email '{data['email']}' is already taken")

        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()

        obj = self._load_with_person(session, user_id)
        return self._to_dto(obj)

    def transition_lifecycle(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None, actor: str,
    ) -> ClientUserDTO:
        """Transition ClientUser lifecycle and record a client_user_lifecycle_event row (D10)."""
        stmt = select(ClientUser).options(joinedload(ClientUser.person)).where(ClientUser.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("ClientUser not found")

        old_state = obj.lifecycle_status
        obj.lifecycle_status = new_state
        session.flush()

        event = ClientUserLifecycleEvent(
            client_user_id=user_id,
            state=new_state,
            reason=reason,
            actor=actor,
        )
        session.add(event)
        session.flush()

        return self._to_dto(obj)

    def delete(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
        actor: str, reason: str | None = None,
    ) -> None:
        """Archive a ClientUser (PO-only). Sets lifecycle_status to 'archived'."""
        stmt = select(ClientUser).where(ClientUser.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("ClientUser not found")

        obj.lifecycle_status = "archived"
        session.flush()

        event = ClientUserLifecycleEvent(
            client_user_id=user_id,
            state="archived",
            reason=reason,
            actor=actor,
        )
        session.add(event)
        session.flush()
