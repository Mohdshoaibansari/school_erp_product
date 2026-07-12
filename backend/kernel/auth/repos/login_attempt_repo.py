"""LoginAttemptRepository (task 8.1, task 8.2).

Inherits TenantAwareRepositoryBase[LoginAttempt]. Methods: record.
Auto-injects client_id from TenantContext. Returns LoginAttemptDTO.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.auth.models.login_attempt import LoginAttempt
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.auth.services.dtos import LoginAttemptDTO


class LoginAttemptRepository(TenantAwareRepositoryBase[LoginAttempt]):
    """Repository for the LoginAttempt entity (Decision 11, Decision 28a).

    Auto-injects client_id from TenantContext. Returns LoginAttemptDTO.
    """

    def __init__(self) -> None:
        super().__init__(LoginAttempt)

    def _to_dto(self, obj: LoginAttempt) -> LoginAttemptDTO:
        return LoginAttemptDTO.model_validate(obj)

    def record(
        self,
        session: Session,
        ctx: TenantContext,
        *,
        email: str,
        event_type: str,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginAttemptDTO:
        """Record a login attempt (D11, D28a, D33)."""
        obj = LoginAttempt(
            client_id=ctx.client_id,
            user_id=user_id,
            email=email,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            occurred_at=datetime.now(timezone.utc),
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)
