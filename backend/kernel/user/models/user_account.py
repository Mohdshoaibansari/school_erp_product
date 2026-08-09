"""UserAccount — shared identity parent for app_user and client_user (D12).

Both app_user and client_user reference user_account.id via FK.
role_assignment.user_id and login_attempt.user_id also reference user_account.id.
This enables cross-tier referential integrity.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class UserAccount(Base):
    """Shared identity anchor for all user types."""

    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
