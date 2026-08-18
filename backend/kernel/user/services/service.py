"""UserService — unified user-lifecycle service (D6, D8, D6a).

Replaces both IdentityUserService and ClientUserService.
Holds a StrategyResolver that dispatches to CDStrategy or InstitutionUserStrategy.

Published service interface for C-02 (A4). Endpoints call services; services
call repos. This is the module boundary other modules see.

Note: UserProfile methods removed (T-18) — user_profile table dropped in migration 022.
Human data lives on person (D6a), accessible via UserDTO.person projection.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session, sessionmaker

from kernel.tenant_context import TenantContext
from kernel.user.repos.role_assignment_repo import RoleAssignmentRepository
from kernel.user.repos.user_identifier_repo import UserIdentifierRepository
from kernel.audit import AuditEmitter, DefaultAuditEmitter

logger = logging.getLogger(__name__)
from kernel.user.services.dtos import (
    UserCreateDTO,
    UserDTO,
    UserUpdateDTO,
    RoleAssignmentCreateDTO,
    RoleAssignmentDTO,
    UserIdentifierCreateDTO,
    UserIdentifierDTO,
    ClientUserCreateDTO,
    ClientUserDTO,
    ClientUserUpdateDTO,
    ClientUserTransitionDTO,
)


class UserService:
    """Unified user-lifecycle service (D6).

    Replaces IdentityUserService and ClientUserService.
    Holds a StrategyResolver and delegates to strategies.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        audit_emitter: AuditEmitter | None = None,
        role_assignment_repo: RoleAssignmentRepository | None = None,
        user_identifier_repo: UserIdentifierRepository | None = None,
        supabase_client=None,  # Optional SupabaseAuthClient
        resolver=None,  # StrategyResolver
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_emitter or DefaultAuditEmitter()
        self._role_assignment_repo = role_assignment_repo or RoleAssignmentRepository(audit_emitter=self._audit)
        self._user_identifier_repo = user_identifier_repo or UserIdentifierRepository(audit_emitter=self._audit)
        self._supabase = supabase_client
        self._resolver = resolver

    @property
    def audit_emitter(self) -> AuditEmitter:
        """Expose the shared audit emitter for tests."""
        return self._audit

    # ---- User CRUD (strategy-dispatched) ----

    def _get_resolver(self):
        """Lazy-init a default resolver for backwards compatibility."""
        if self._resolver is None:
            from kernel.user.services.strategies.cd_strategy import CDStrategy
            from kernel.user.services.strategies.institution_strategy import InstitutionUserStrategy
            from kernel.user.services.strategies.resolver import StrategyResolver
            cd_strategy = CDStrategy(
                session_factory=self._session_factory,
                supabase_client=self._supabase,
                audit_emitter=self._audit,
            )
            institution_strategy = InstitutionUserStrategy(
                session_factory=self._session_factory,
                supabase_client=self._supabase,
                audit_emitter=self._audit,
            )
            self._resolver = StrategyResolver(
                cd_strategy=cd_strategy,
                institution_strategy=institution_strategy,
                session_factory=self._session_factory,
            )
        return self._resolver

    async def create_user(self, ctx: TenantContext, dto) -> dict:
        """Create a user. Dispatches to the appropriate strategy by DTO type."""
        strategy = self._get_resolver().resolve_for_create(dto)
        return await strategy.create_user(ctx, dto)

    def get_user(self, ctx: TenantContext, user_id: uuid.UUID):
        """Get a user by ID. Uses DB lookup to dispatch."""
        resolver = self._get_resolver()
        with self._session_factory() as session:
            from kernel.user.models.client_user import ClientUser
            cuser = session.get(ClientUser, user_id)
            if cuser:
                return resolver._cd.get_user(ctx, user_id)
            return resolver._inst.get_user(ctx, user_id)

    def list_users(self, ctx: TenantContext, **filters):
        """List users. Currently returns institution users (backwards compat)."""
        resolver = self._get_resolver()
        if "client_id" in filters:
            return resolver._cd.list_users(ctx, **filters)
        return resolver._inst.list_users(ctx, **filters)

    async def delete_user(self, ctx: TenantContext, user_id: uuid.UUID) -> None:
        """Delete a user. Dispatches by DB lookup."""
        strategy = await self._get_resolver().resolve_for_other(ctx, user_id)
        await strategy.delete_user(ctx, user_id)

    async def update_user(
        self, ctx: TenantContext, user_id: uuid.UUID, dto,
    ):
        """Update a user. Dispatches by DB lookup."""
        strategy = await self._get_resolver().resolve_for_other(ctx, user_id)
        return await strategy.update_user(ctx, user_id, dto)

    async def transition_lifecycle(
        self, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None,
    ):
        """Transition user lifecycle. Dispatches by DB lookup."""
        strategy = await self._get_resolver().resolve_for_other(ctx, user_id)
        return await strategy.transition_lifecycle(ctx, user_id, new_state, reason)

    # ---- RoleAssignment ----

    def create_role_assignment(
        self, ctx: TenantContext, user_id: uuid.UUID, dto: RoleAssignmentCreateDTO,
    ) -> RoleAssignmentDTO:
        """Create a RoleAssignment for a User."""
        with self._session_factory() as session:
            result = self._role_assignment_repo.create(session, ctx, user_id, dto)
            session.commit()
            return result

    def list_role_assignments(
        self, ctx: TenantContext, user_id: uuid.UUID,
    ) -> list[RoleAssignmentDTO]:
        """List RoleAssignments for a User."""
        with self._session_factory() as session:
            return self._role_assignment_repo.list_by_user(session, ctx, user_id)

    def delete_role_assignment(
        self, ctx: TenantContext, assignment_id: uuid.UUID,
    ) -> None:
        """Delete a RoleAssignment."""
        with self._session_factory() as session:
            self._role_assignment_repo.delete(session, ctx, assignment_id)
            session.commit()

    # ---- UserIdentifier ----

    def create_identifier(
        self, ctx: TenantContext, user_id: uuid.UUID, dto: UserIdentifierCreateDTO,
    ) -> UserIdentifierDTO:
        """Create a UserIdentifier for a User."""
        with self._session_factory() as session:
            result = self._user_identifier_repo.create(session, ctx, user_id, dto)
            session.commit()
            return result

    def list_identifiers(
        self, ctx: TenantContext, user_id: uuid.UUID,
    ) -> list[UserIdentifierDTO]:
        """List UserIdentifiers for a User."""
        with self._session_factory() as session:
            return self._user_identifier_repo.list_by_user(session, ctx, user_id)

    def delete_identifier(
        self, ctx: TenantContext, identifier_id: uuid.UUID,
    ) -> None:
        """Delete a UserIdentifier."""
        with self._session_factory() as session:
            self._user_identifier_repo.delete(session, ctx, identifier_id)
            session.commit()
