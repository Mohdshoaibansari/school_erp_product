"""CDStrategy — client-leadership tier user operations (D6, D8, D6a).

Operates on the client_user table. Implements the full UserStrategy interface.
Person-first insert order (D3a): the repo handles person → user_account → client_user.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session, sessionmaker

from kernel.tenant_context import TenantContext
from kernel.user.repos.client_user_repo import ClientUserRepository
from kernel.user.services.dtos import (
    ClientUserCreateDTO,
    ClientUserDTO,
    ClientUserUpdateDTO,
    ClientUserTransitionDTO,
)
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from kernel.auth.supabase_client import SupabaseAuthError

logger = logging.getLogger(__name__)


class CDStrategy:
    """Strategy for client-leadership tier users (client_user table)."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repo: ClientUserRepository | None = None,
        supabase_client=None,
        audit_emitter: AuditEmitter | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._repo = repo or ClientUserRepository()
        self._supabase = supabase_client
        self._audit = audit_emitter or DefaultAuditEmitter()

    async def create_user(self, ctx: TenantContext, dto: ClientUserCreateDTO) -> dict:
        """Create a client-leadership user (CD bootstrap).

        Person-first insert order (D3a): repo handles person → user_account → client_user.
        Returns {"user": ClientUserDTO, "invite_url": str}.
        """
        user_id = uuid.uuid4()
        email = dto.email
        client_id = ctx.client_id or dto.client_id

        # 1. Insert client_user row + role_assignment
        with self._session_factory() as session:
            user_dto = self._repo.create(session, ctx, ClientUserCreateDTO(
                email=email,
                person_data=dto.person_data,
                role_id=dto.role_id,
                client_id=client_id,
            ), user_id=user_id)

            # Assign role if provided (same pattern as InstitutionUserStrategy)
            if dto.role_id is not None:
                from sqlalchemy import text as sa_text
                role_row = session.execute(
                    sa_text("SELECT id FROM role WHERE id = :rid"),
                    {"rid": str(dto.role_id)},
                ).fetchone()
                if not role_row:
                    session.rollback()
                    raise ValueError(f"Role not found: {dto.role_id}")
                session.execute(sa_text(
                    "INSERT INTO role_assignment (id, client_id, user_id, role_id, scope) "
                    "VALUES (gen_random_uuid(), :cid, :uid, :rid, NULL)"
                ), {
                    "cid": client_id,
                    "uid": user_id,
                    "rid": dto.role_id,
                })

            # Record lifecycle event (invited state)
            from kernel.user.models.client_user_lifecycle_event import ClientUserLifecycleEvent
            event = ClientUserLifecycleEvent(
                client_user_id=user_dto.id,
                state="invited",
                reason="Bootstrap by Platform Owner",
                actor=str(ctx.user_id or "platform_owner"),
            )
            session.add(event)
            session.commit()

        # 3. Mint invite JWT
        from kernel.auth.services.invite_token import mint_invite_token
        invite_jwt = mint_invite_token(user_id, email)

        # 4. Build invite URL from config
        from kernel.config.resolver import config
        try:
            frontend_url = config.get("app.activationBaseUrl")
        except KeyError:
            frontend_url = "http://127.0.0.1:8000"
        invite_url = f"{frontend_url}/activate?token={invite_jwt}"

        # 5. Emit audit (use person.name from DTO, D6a)
        self._audit.emit(
            action="user_created",
            client_id=client_id,
            institution_id=None,
            actor=ctx.user_id,
            payload={
                "user_id": str(user_id),
                "email": email,
                "name": user_dto.person.name,
                "client_id": str(client_id),
            },
        )

        logger.info("[CDStrategy] Bootstrap complete: user_id=%s client_id=%s", user_id, client_id)
        return {"user": user_dto, "invite_url": invite_url}

    async def update_user(
        self, ctx: TenantContext, user_id: uuid.UUID, dto: ClientUserUpdateDTO,
    ) -> ClientUserDTO:
        """Update a client-leadership user."""
        with self._session_factory() as session:
            result = self._repo.update(session, ctx, user_id, dto)
            session.commit()
            return result

    async def delete_user(self, ctx: TenantContext, user_id: uuid.UUID) -> None:
        """Revoke a client-leadership user: archive client_user row + delete Supabase Auth user.

        Note: Person row is NOT deleted — person is the enduring anchor (D3a).
        """
        actor = str(ctx.user_id or "platform_owner")
        auth_deleted = False
        try:
            if self._supabase:
                await self._supabase.delete_user(user_id)
                auth_deleted = True
                logger.info("[CDStrategy] Auth user deleted: uid=%s", user_id)
        except Exception as e:
            logger.warning("[CDStrategy] Auth delete failed (archiving anyway): uid=%s error=%s",
                           user_id, str(e)[:120])

        with self._session_factory() as session:
            self._repo.delete(session, ctx, user_id, actor=actor)
            session.commit()
            logger.info("[CDStrategy] Revoked: uid=%s auth_deleted=%s", user_id, auth_deleted)

    def get_user(self, ctx: TenantContext, user_id: uuid.UUID) -> ClientUserDTO | None:
        """Get a client-leadership user by ID."""
        with self._session_factory() as session:
            return self._repo.get_by_id(session, ctx, user_id)

    def list_users(self, ctx: TenantContext, **filters) -> list[ClientUserDTO]:
        """List client-leadership users for the given client."""
        client_id = filters.pop("client_id", None)
        with self._session_factory() as session:
            if client_id:
                return self._repo.list_by_client(session, ctx, client_id)
            return []

    async def transition_lifecycle(
        self, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None,
    ) -> ClientUserDTO:
        """Transition a client-leadership user's lifecycle."""
        actor = str(ctx.user_id or "platform_owner")
        with self._session_factory() as session:
            result = self._repo.transition_lifecycle(
                session, ctx, user_id,
                new_state=new_state,
                reason=reason,
                actor=actor,
            )
            session.commit()

        self._audit.emit(
            action="user_transitioned",
            client_id=ctx.client_id or result.client_id,
            institution_id=None,
            actor=ctx.user_id,
            payload={
                "user_id": str(user_id),
                "to_state": new_state,
                "reason": reason,
            },
        )

        return result
