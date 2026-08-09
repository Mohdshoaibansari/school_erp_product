"""UserStrategy Protocol — full-symmetric strategy interface (D8).

Both CDStrategy and InstitutionUserStrategy implement this interface.
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from kernel.tenant_context import TenantContext


class UserStrategy(Protocol):
    """Full-symmetric strategy interface (D8).

    Implemented by CDStrategy and InstitutionUserStrategy.
    Every method on both strategies.
    """

    async def create_user(self, ctx: TenantContext, dto: Any) -> dict[str, Any]:
        """Create a new user. Returns {"user": DTO, "invite_url": str}."""
        ...

    async def update_user(self, ctx: TenantContext, user_id: uuid.UUID, dto: Any) -> Any:
        """Update a user. Returns the user DTO."""
        ...

    async def delete_user(self, ctx: TenantContext, user_id: uuid.UUID) -> None:
        """Delete a user and all related data."""
        ...

    def get_user(self, ctx: TenantContext, user_id: uuid.UUID) -> Any | None:
        """Get a user by ID."""
        ...

    def list_users(self, ctx: TenantContext, **filters: Any) -> list[Any]:
        """List users, tenant-filtered."""
        ...

    async def transition_lifecycle(
        self, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None,
    ) -> Any:
        """Transition user lifecycle. Returns the updated user DTO."""
        ...
