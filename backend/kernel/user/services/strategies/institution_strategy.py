"""InstitutionUserStrategy — institution tier user operations (D6, D8).

Operates on the app_user table. Implements the full UserStrategy interface.
Moves logic from the existing IdentityUserService.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session, sessionmaker

from kernel.tenant_context import TenantContext
from kernel.user.repos.user_repo import UserRepository
from kernel.user.services.dtos import (
    UserCreateDTO,
    UserDTO,
    UserUpdateDTO,
)
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from kernel.auth.supabase_client import SupabaseAuthError

logger = logging.getLogger(__name__)


class InstitutionUserStrategy:
    """Strategy for institution-tier users (app_user table)."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        user_repo: UserRepository | None = None,
        supabase_client=None,
        audit_emitter: AuditEmitter | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._user_repo = user_repo or UserRepository(audit_emitter=audit_emitter or DefaultAuditEmitter())
        self._supabase = supabase_client
        self._audit = audit_emitter or DefaultAuditEmitter()

    async def create_user(self, ctx: TenantContext, dto: UserCreateDTO) -> dict:
        """Create an institution user.

        Validates role BEFORE Supabase call (D10 bug #6).
        Returns {"user": UserDTO, "invite_url": str}.
        """
        with self._session_factory() as session:
            result = self._user_repo.create(session, ctx, dto)

            # D2: Assign role atomically if role_id provided
            if dto.role_id is not None:
                from sqlalchemy import text as sa_text
                # Validate role exists BEFORE Supabase call (D10 bug #6)
                role_row = session.execute(
                    sa_text("SELECT id FROM role WHERE id = :rid"),
                    {"rid": str(dto.role_id)},
                ).fetchone()
                if not role_row:
                    session.rollback()
                    raise ValueError(f"Role not found: {dto.role_id}")

                # Insert role_assignment in same transaction
                session.execute(sa_text(
                    "INSERT INTO role_assignment (id, client_id, user_id, role_id, scope) "
                    "VALUES (gen_random_uuid(), :cid, :uid, :rid, NULL)"
                ), {
                    "cid": ctx.client_id,
                    "uid": result.id,
                    "rid": dto.role_id,
                })

            # D1/D3: Mint invite JWT and build invite URL
            # D11: Supabase Auth user is created during activate (with password), not here.
            from kernel.auth.services.invite_token import mint_invite_token
            from kernel.config.resolver import config
            invite_jwt = mint_invite_token(result.id, result.email)
            try:
                frontend_url = config.get("app.activationBaseUrl")
            except KeyError:
                frontend_url = "http://127.0.0.1:8000"
            invite_url = f"{frontend_url}/activate?token={invite_jwt}"

            session.commit()

            # C-11 audit emission for user creation (AC-10)
            self._audit.emit(
                action="user_created",
                client_id=ctx.client_id,
                institution_id=ctx.institution_id,
                actor=ctx.user_id,
                payload={
                    "user_id": str(result.id),
                    "email": result.email,
                    "name": result.name,
                    "institution_id": str(dto.institution_id),
                },
            )

            return {"user": result, "invite_url": invite_url}

    def get_user(self, ctx: TenantContext, user_id: uuid.UUID) -> UserDTO | None:
        """Get an institution user by ID."""
        with self._session_factory() as session:
            return self._user_repo.get(session, ctx, user_id)

    def list_users(self, ctx: TenantContext, **filters) -> list[UserDTO]:
        """List institution users, tenant-filtered."""
        with self._session_factory() as session:
            return self._user_repo.list(session, ctx, **filters)

    async def delete_user(self, ctx: TenantContext, user_id: uuid.UUID) -> None:
        """Delete an institution user and all related data (D20b cascade)."""
        from sqlalchemy import text as sa_text

        logger.info("[InstitutionStrategy] Deleting user: id=%s", user_id)

        with self._session_factory() as session:
            user_dto = self._user_repo.get(session, ctx, user_id)
            if not user_dto:
                raise ValueError("User not found")

            # Delete related records (cascade order — FKs first)
            session.execute(sa_text("DELETE FROM login_attempt WHERE user_id = :uid"), {"uid": user_id})
            session.execute(sa_text("DELETE FROM role_assignment WHERE user_id = :uid"), {"uid": user_id})
            session.execute(sa_text("DELETE FROM user_identifier WHERE user_id = :uid"), {"uid": user_id})
            session.execute(sa_text("DELETE FROM user_profile WHERE user_id = :uid"), {"uid": user_id})
            session.execute(sa_text("DELETE FROM user_lifecycle_event WHERE user_id = :uid"), {"uid": user_id})

            # Delete Supabase Auth user
            if self._supabase:
                try:
                    await self._supabase.delete_user(user_id)
                    logger.info("[InstitutionStrategy] Supabase Auth user deleted: id=%s", user_id)
                except Exception as e:
                    logger.warning("[InstitutionStrategy] Failed to delete Supabase Auth user: id=%s error=%s",
                                   user_id, str(e)[:100])

            # Delete app_user
            session.execute(sa_text("DELETE FROM app_user WHERE id = :uid"), {"uid": user_id})
            session.commit()

            logger.info("[InstitutionStrategy] User deleted: id=%s", user_id)

    async def update_user(
        self, ctx: TenantContext, user_id: uuid.UUID, dto: UserUpdateDTO,
    ) -> UserDTO:
        """Update an institution user. Propagates email changes to Supabase."""
        with self._session_factory() as session:
            current_user = self._user_repo.get(session, ctx, user_id)
            if not current_user:
                raise ValueError(f"User {user_id} not found")

            result = self._user_repo.update(session, ctx, user_id, dto)

            # Phase 4 (12.5): Propagate email change to Supabase Auth
            if (
                self._supabase is not None
                and dto.email is not None
                and dto.email != current_user.email
            ):
                try:
                    await self._supabase.update_user(
                        user_id, email=dto.email, email_confirm=False,
                    )
                except Exception as e:
                    session.rollback()
                    raise ValueError(f"Failed to propagate email change to Supabase: {e}") from e

            session.commit()
            return result

    async def transition_lifecycle(
        self, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None,
    ) -> UserDTO:
        """Transition institution user lifecycle. Propagates suspend/archive to Supabase."""
        with self._session_factory() as session:
            result = self._user_repo.transition_lifecycle(
                session, ctx, user_id, new_state, reason, ctx.user_id or "unknown",
            )

            # Phase 4 (12.3, 12.4): Propagate suspend/archive to Supabase Auth
            if self._supabase is not None:
                try:
                    if new_state == "suspended":
                        await self._supabase.sign_out(user_id, "global")
                    elif new_state == "archived":
                        await self._supabase.sign_out(user_id, "global")
                        await self._supabase.delete_user(user_id)
                except Exception as e:
                    session.rollback()
                    raise ValueError(f"Failed to propagate {new_state} to Supabase: {e}") from e

            session.commit()
            return result
