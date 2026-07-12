"""IdentityUserService (task 8.1, task 8.2).

Published service interface for C-02 (A4). Endpoints call services; services
call repos. This is the module boundary other modules see.

Methods: create_user, get_user, list_users, update_user, transition_lifecycle,
create_profile, get_profile, update_profile, create_role_assignment,
list_role_assignments, delete_role_assignment, create_identifier,
list_identifiers, delete_identifier.

Wires audit emission via AuditEmitter Protocol (task 8.2).

Phase 4 (C-03): Optional SupabaseAuthClient for admin propagation to Supabase Auth.
When injected, create_user/transition_lifecycle/update_user propagate to Supabase.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, sessionmaker

from kernel.tenant_context import TenantContext
from kernel.user.repos.user_repo import UserRepository
from kernel.user.repos.user_profile_repo import UserProfileRepository
from kernel.user.repos.role_assignment_repo import RoleAssignmentRepository
from kernel.user.repos.user_identifier_repo import UserIdentifierRepository
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from kernel.auth.supabase_client import SupabaseAuthClient, SupabaseAuthError
from kernel.user.services.dtos import (
    UserCreateDTO,
    UserDTO,
    UserUpdateDTO,
    UserProfileCreateDTO,
    UserProfileDTO,
    UserProfileUpdateDTO,
    RoleAssignmentCreateDTO,
    RoleAssignmentDTO,
    UserIdentifierCreateDTO,
    UserIdentifierDTO,
)


class IdentityUserService:
    """Published service interface for C-02 (A4).

    Endpoints call this; it orchestrates repos + TenantContext.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        audit_emitter: AuditEmitter | None = None,
        user_repo: UserRepository | None = None,
        profile_repo: UserProfileRepository | None = None,
        role_assignment_repo: RoleAssignmentRepository | None = None,
        user_identifier_repo: UserIdentifierRepository | None = None,
        supabase_client: SupabaseAuthClient | None = None,  # Phase 4 (12.1)
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_emitter or DefaultAuditEmitter()
        self._user_repo = user_repo or UserRepository(audit_emitter=self._audit)
        self._profile_repo = profile_repo or UserProfileRepository()
        self._role_assignment_repo = role_assignment_repo or RoleAssignmentRepository(audit_emitter=self._audit)
        self._user_identifier_repo = user_identifier_repo or UserIdentifierRepository(audit_emitter=self._audit)
        self._supabase = supabase_client  # Phase 4 (12.1) — optional, backwards compatible

    @property
    def audit_emitter(self) -> AuditEmitter:
        """Expose the shared audit emitter for tests."""
        return self._audit

    # ---- User CRUD ----

    async def create_user(self, ctx: TenantContext, dto: UserCreateDTO) -> UserDTO:
        """Create a new User.

        Phase 4 (12.2): If SupabaseAuthClient is injected, creates the
        matching Supabase Auth user. On Supabase failure, rolls back the
        app_user insert and raises.
        """
        with self._session_factory() as session:
            result = self._user_repo.create(session, ctx, dto)

            # Phase 4 (12.2): Propagate to Supabase Auth
            if self._supabase is not None:
                try:
                    await self._supabase.create_user(result.id, result.email)
                except SupabaseAuthError as e:
                    session.rollback()  # Rollback app_user insert
                    raise ValueError(f"Failed to create Supabase Auth user: {e}") from e

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
                },
            )

            return result

    def get_user(self, ctx: TenantContext, user_id: uuid.UUID) -> UserDTO | None:
        """Get a User by id."""
        with self._session_factory() as session:
            return self._user_repo.get(session, ctx, user_id)

    def list_users(self, ctx: TenantContext, **filters) -> list[UserDTO]:
        """List Users, tenant-filtered."""
        with self._session_factory() as session:
            return self._user_repo.list(session, ctx, **filters)

    async def update_user(
        self, ctx: TenantContext, user_id: uuid.UUID, dto: UserUpdateDTO,
    ) -> UserDTO:
        """Update a User.

        Phase 4 (12.5): If SupabaseAuthClient is injected and email changes,
        propagates to Supabase Auth.
        """
        with self._session_factory() as session:
            # Get current user to check if email changed
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
                except SupabaseAuthError as e:
                    session.rollback()
                    raise ValueError(f"Failed to propagate email change to Supabase: {e}") from e

            session.commit()
            return result

    async def transition_lifecycle(
        self, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None,
    ) -> UserDTO:
        """Transition User lifecycle.

        Phase 4 (12.3, 12.4): If SupabaseAuthClient is injected and the
        new state is suspended or archived, propagates to Supabase Auth.
        """
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
                except SupabaseAuthError as e:
                    session.rollback()
                    raise ValueError(f"Failed to propagate {new_state} to Supabase: {e}") from e

            session.commit()
            return result

    # ---- UserProfile ----

    def create_profile(
        self, ctx: TenantContext, user_id: uuid.UUID, dto: UserProfileCreateDTO,
    ) -> UserProfileDTO:
        """Create a UserProfile for a User."""
        with self._session_factory() as session:
            result = self._profile_repo.create(session, ctx, user_id, dto)
            session.commit()
            return result

    def get_profile(self, ctx: TenantContext, user_id: uuid.UUID) -> UserProfileDTO | None:
        """Get a UserProfile by user_id."""
        with self._session_factory() as session:
            return self._profile_repo.get_by_user_id(session, ctx, user_id)

    def update_profile(
        self, ctx: TenantContext, user_id: uuid.UUID, dto: UserProfileUpdateDTO,
    ) -> UserProfileDTO:
        """Update a UserProfile."""
        with self._session_factory() as session:
            result = self._profile_repo.update(session, ctx, user_id, dto)
            session.commit()
            return result

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
