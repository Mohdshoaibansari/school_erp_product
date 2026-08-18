"""UserRepository (task 7.1, T-15 modified).

Inherits TenantAwareRepositoryBase[User]. Methods: create, get, list, update, transition_lifecycle.
Auto-injects client_id from TenantContext. Returns UserDTO.

Person-first insert order (D3a, D3f): person → user_account → app_user.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from kernel.tenant_context import TenantContext
from kernel.user.models.user import User
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from kernel.user.services.dtos import UserCreateDTO, UserDTO, UserUpdateDTO, PersonDTO


class UserRepository(TenantAwareRepositoryBase[User]):
    """Repository for the User entity (Decision 1, Decision 4, D6a).

    Auto-injects client_id from TenantContext. Returns UserDTO.
    Person-first insert order: person → user_account → app_user.
    """

    def __init__(self, audit_emitter: AuditEmitter | None = None,
                 person_repo=None) -> None:
        super().__init__(User)
        self._audit = audit_emitter or DefaultAuditEmitter()
        self._person_repo = person_repo

    def _get_person_repo(self):
        if self._person_repo is None:
            from kernel.user.repos.person_repo import PersonRepository
            self._person_repo = PersonRepository()
        return self._person_repo

    def _to_dto(self, obj: User) -> UserDTO:
        """Convert ORM User to UserDTO with person projection."""
        person_dto = None
        if obj.person is not None:
            person_dto = PersonDTO.model_validate(obj.person)
        else:
            # Fallback: create a minimal person DTO
            person_dto = PersonDTO(
                id=obj.person_id or uuid.UUID(int=0),
                client_id=obj.client_id,
                name="Unknown",
                status="Active",
                created_at=obj.created_at,
                updated_at=obj.updated_at,
            )
        return UserDTO(
            id=obj.id,
            client_id=obj.client_id,
            institution_id=obj.institution_id,
            email=obj.email,
            person=person_dto,
            lifecycle_status=obj.lifecycle_status,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    def _load_user_with_person(self, session: Session, user_id: uuid.UUID) -> User | None:
        """Load user with eagerly loaded person relationship."""
        return session.execute(
            select(User)
            .options(joinedload(User.person))
            .where(User.id == user_id)
        ).scalars().first()

    def create(self, session: Session, ctx: TenantContext, dto: UserCreateDTO, *, user_id: uuid.UUID | None = None) -> UserDTO:
        """Create a new User with person-first insert order (D3a, D3f).

        Insert order: person → user_account → app_user.
        """
        # Check email uniqueness
        existing = session.execute(
            select(User).where(User.email == dto.email)
        ).scalars().first()
        if existing:
            raise ValueError(f"Email '{dto.email}' is already taken")

        # 1. Insert person first (independent UUID, D3a)
        person_repo = self._get_person_repo()
        person_dto = person_repo.create(session, ctx, dto.person_data)

        uid = user_id or uuid.uuid4()

        # 2. D12: Insert user_account parent row
        from sqlalchemy import text as sa_text
        session.execute(sa_text(
            "INSERT INTO user_account (id) VALUES (:id) ON CONFLICT (id) DO NOTHING"
        ), {"id": uid})

        # 3. Insert app_user with person_id (no name, no user_category_id)
        obj = User(
            id=uid,
            client_id=ctx.client_id,
            institution_id=dto.institution_id,
            email=dto.email,
            person_id=person_dto.id,
            lifecycle_status="invited",
        )
        session.add(obj)
        session.flush()

        # Reload with person eagerly loaded
        obj = self._load_user_with_person(session, uid)
        return self._to_dto(obj)

    def get(self, session: Session, ctx: TenantContext, user_id: uuid.UUID) -> UserDTO | None:
        """Get a User by ID with person projection."""
        stmt = select(User).options(joinedload(User.person)).where(User.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def list(self, session: Session, ctx: TenantContext, **filters) -> list[UserDTO]:
        """List Users with person projection, tenant-filtered."""
        stmt = select(User).options(joinedload(User.person))
        stmt = self._apply_tenant_filter(stmt, ctx)
        if "lifecycle_status" in filters:
            stmt = stmt.where(User.lifecycle_status == filters["lifecycle_status"])
        objs = session.execute(stmt).scalars().unique().all()
        return [self._to_dto(obj) for obj in objs]

    def get_by_email(self, session: Session, email: str) -> UserDTO | None:
        """Get a User by email (not tenant-filtered — email is globally unique)."""
        stmt = select(User).options(joinedload(User.person)).where(User.email == email)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def update(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID, dto: UserUpdateDTO,
    ) -> UserDTO:
        """Update User identity fields. Name changes route to person (D6a)."""
        stmt = select(User).options(joinedload(User.person)).where(User.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("User not found")

        data = dto.model_dump(exclude_unset=True)

        # Route name to person
        if "name" in data and data["name"] is not None:
            person_repo = self._get_person_repo()
            person_repo.update(session, ctx, obj.person_id, {"name": data.pop("name")})

        # Check email uniqueness if email is being changed
        if "email" in data and data["email"] != obj.email:
            existing = session.execute(
                select(User).where(User.email == data["email"], User.id != user_id)
            ).scalars().first()
            if existing:
                raise ValueError(f"Email '{data['email']}' is already taken")

        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()

        # Reload with person
        obj = self._load_user_with_person(session, user_id)
        return self._to_dto(obj)

    def transition_lifecycle(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None, actor: str,
    ) -> UserDTO:
        """Transition User lifecycle (Decision 8, AC-10, AC-11)."""
        from kernel.user.services.state_machine import validate_user_transition

        stmt = select(User).options(joinedload(User.person)).where(User.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("User not found")

        old_state = obj.lifecycle_status
        validate_user_transition(old_state, new_state)

        obj.lifecycle_status = new_state
        session.flush()

        # Record lifecycle event
        from kernel.user.models.user_lifecycle_event import UserLifecycleEvent
        event = UserLifecycleEvent(
            client_id=obj.client_id,
            user_id=obj.id,
            state=new_state,
            reason=reason,
            actor=actor,
        )
        session.add(event)
        session.flush()

        # C-11 audit emission
        self._audit.emit(
            action="user_lifecycle_transition",
            client_id=obj.client_id,
            institution_id=obj.institution_id,
            actor=actor,
            payload={
                "user_id": str(obj.id),
                "from_state": old_state,
                "to_state": new_state,
                "reason": reason,
                "actor": actor,
            },
        )

        return self._to_dto(obj)
