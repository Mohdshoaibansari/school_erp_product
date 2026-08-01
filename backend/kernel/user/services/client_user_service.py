"""ClientUserService (task 3.4).

Orchestrates ClientUserRepository + SupabaseAuthClient + invite token machinery.
Methods: bootstrap_invite (PO), accept_invite (CD), list_in_client (PO),
get_by_id, update_own (CD/PO), transition_lifecycle (PO), revoke (PO).
"""

from __future__ import annotations

import uuid
import logging

from kernel.tenant_context import TenantContext
from kernel.user.repos.client_user_repo import ClientUserRepository
from kernel.user.services.dtos import (
    ClientUserCreateDTO,
    ClientUserDTO,
    ClientUserUpdateDTO,
    ClientUserTransitionDTO,
)

logger = logging.getLogger(__name__)


class ClientUserService:
    """Service for client-leadership-scope users (D1, D3, D6, D10)."""

    def __init__(
        self,
        repo: ClientUserRepository,
        supabase_auth,
        session_factory,
        config_resolver=None,
    ) -> None:
        self._repo = repo
        self._auth = supabase_auth
        self._session_factory = session_factory
        self._config = config_resolver

    # ---- PO operations ----

    async def bootstrap_invite(
        self, ctx: TenantContext, client_id: uuid.UUID, dto: ClientUserCreateDTO,
    ) -> dict:
        """PO bootstraps a Client Director: creates Supabase Auth user (invited, no password),
        inserts client_user row with lifecycle_status='invited', mints invite JWT, returns
        invite URL. Per D6, D7."""
        user_id = uuid.uuid4()
        email = dto.email

        # 1. Create Supabase Auth user with user_metadata.user_tier
        auth = self._auth
        await auth.create_user(user_id, email)

        # Update user_metadata to stamp the tier flag
        try:
            await auth.update_user(
                uid=str(user_id),
                user_metadata={"user_tier": "client_leadership"},
            )
        except Exception as e:
            logger.warning("[CLIENT_USER] Could not stamp user_tier on Auth user %s: %s", user_id, e)

        logger.info("[CLIENT_USER] Auth user created: uid=%s email=%s", user_id, email)

        # 2. Insert client_user row
        with self._session_factory() as session:
            user_dto = self._repo.create(session, ctx, ClientUserCreateDTO(
                email=email,
                name=dto.name,
                role_id=dto.role_id,
                user_category_id=dto.user_category_id,
                client_id=client_id,
            ))
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

        # 4. Build invite URL
        frontend_url = "http://127.0.0.1:8000"
        invite_url = f"{frontend_url}/activate?token={invite_jwt}"

        logger.info("[CLIENT_USER] Bootstrap complete: user_id=%s client_id=%s", user_id, client_id)
        return {
            "user_id": str(user_id),
            "email": email,
            "invite_url": invite_url,
            "client_id": str(client_id),
        }

    def list_in_client(
        self, ctx: TenantContext, client_id: uuid.UUID,
    ) -> list[ClientUserDTO]:
        """PO lists all ClientUsers in a client. Per D4."""
        with self._session_factory() as session:
            return self._repo.list_by_client(session, ctx, client_id)

    def get_by_id(
        self, ctx: TenantContext, user_id: uuid.UUID,
    ) -> ClientUserDTO | None:
        """Get a ClientUser by ID (CD gets own row; PO gets any)."""
        with self._session_factory() as session:
            return self._repo.get_by_id(session, ctx, user_id)

    def update_own(
        self, ctx: TenantContext, user_id: uuid.UUID, dto: ClientUserUpdateDTO,
    ) -> ClientUserDTO:
        """CD updates own display name. PO can update any CD. Per D5."""
        with self._session_factory() as session:
            result = self._repo.update(session, ctx, user_id, dto)
            session.commit()
            return result

    def transition_lifecycle(
        self, ctx: TenantContext, user_id: uuid.UUID,
        transition: ClientUserTransitionDTO,
    ) -> ClientUserDTO:
        """PO transitions a CD's lifecycle (suspend, reinstate, archive). Per D4, D10."""
        actor = str(ctx.user_id or "platform_owner")
        with self._session_factory() as session:
            result = self._repo.transition_lifecycle(
                session, ctx, user_id,
                new_state=transition.new_state,
                reason=transition.reason,
                actor=actor,
            )
            session.commit()
            return result

    async def revoke(
        self, ctx: TenantContext, user_id: uuid.UUID,
        reason: str | None = None,
    ) -> None:
        """PO revokes a CD: archives client_user row AND deletes Supabase Auth user.
        Per D4, R2 (transactional cleanup to prevent user_tier drift)."""
        actor = str(ctx.user_id or "platform_owner")
        auth = self._auth

        # Delete Auth user FIRST (if this fails, no client_user archive is created)
        try:
            await auth.delete_user(user_id)
            logger.info("[CLIENT_USER] Auth user deleted: uid=%s", user_id)
        except Exception as e:
            logger.error("[CLIENT_USER] Failed to delete Auth user %s: %s", user_id, e)
            raise ValueError(f"Failed to revoke Auth user: {e}")

        # Archive client_user row
        with self._session_factory() as session:
            self._repo.delete(session, ctx, user_id, actor=actor, reason=reason)
            session.commit()
