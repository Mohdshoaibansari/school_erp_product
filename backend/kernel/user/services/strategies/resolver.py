"""StrategyResolver — dispatches to CDStrategy or InstitutionUserStrategy (D7).

For create_user: dispatches by DTO type.
For other operations: dispatches by DB lookup (reads tier from user record).
Long-term target: Organization.type via Membership (future capability).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, sessionmaker

from kernel.tenant_context import TenantContext
from kernel.user.services.dtos import ClientUserCreateDTO, UserCreateDTO
from kernel.user.services.strategies.base import UserStrategy


class StrategyResolver:
    """Resolves the correct strategy for a user operation."""

    def __init__(
        self,
        cd_strategy: UserStrategy,
        institution_strategy: UserStrategy,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self._cd = cd_strategy
        self._inst = institution_strategy
        self._session_factory = session_factory

    def resolve_for_create(self, dto) -> UserStrategy:
        """Dispatch by DTO type for create_user."""
        if isinstance(dto, ClientUserCreateDTO):
            return self._cd
        if isinstance(dto, UserCreateDTO):
            return self._inst
        raise TypeError(f"Unknown DTO type for create_user: {type(dto)}")

    async def resolve_for_other(self, ctx: TenantContext, user_id: uuid.UUID) -> UserStrategy:
        """Dispatch by DB lookup for update/get/delete/list/transition.

        Reads the user record by ID to determine tier.
        """
        tier = await self._read_tier(ctx, user_id)
        if tier == "client_leadership":
            return self._cd
        if tier == "institution":
            return self._inst
        raise ValueError(f"Unknown tier for user {user_id}: {tier}")

    async def _read_tier(self, ctx: TenantContext, user_id: uuid.UUID) -> str:
        """Read the tier from the user record.

        Checks client_user first, then app_user.
        """
        if self._session_factory is None:
            raise RuntimeError("session_factory is required for DB lookup dispatch")

        from sqlalchemy import text as sa_text

        with self._session_factory() as session:
            # Check client_user first
            row = session.execute(
                sa_text("SELECT 1 FROM client_user WHERE id = :uid"),
                {"uid": user_id},
            ).fetchone()
            if row is not None:
                return "client_leadership"

            # Check app_user
            row = session.execute(
                sa_text("SELECT 1 FROM app_user WHERE id = :uid"),
                {"uid": user_id},
            ).fetchone()
            if row is not None:
                return "institution"

            raise ValueError(f"User {user_id} not found in client_user or app_user")
