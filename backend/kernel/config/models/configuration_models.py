"""C-08 Configuration Framework — ORM models.

Three tables:
- ConfigurationKey: registry of all named settings (key, type, default, category, ...)
- ConfigurationValue: scope-bound override of a key (Platform/Client/Institution)
- ConfigurationAudit: append-only change log

Per the PRD (docs/prd/c-08-configuration-framework.md §5):
- type: string | number | boolean | json | date
- merge_strategy: replace | append_lists | deep_merge
- category: Business Rules | Display | Academic | Notifications | Feature Toggles | Platform | Integrations
- scope_type: platform | client | institution  (module scope deferred to Phase 2)
- action: key_created | key_updated | key_deprecated | value_created | value_updated | value_deleted
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


# ============================================================
# ENUM type definitions (PostgreSQL ENUMs created in migration 009)
# ============================================================
# These match the ENUMs created by migration 009_c08_configuration.py.
# The enum values are NOT re-created by SQLAlchemy because the migration
# already created them. If the enum is missing, the table will fail to
# create — so migration 009 must run first.

CONFIGURATION_TYPE = SAEnum(
    "string", "number", "boolean", "json", "date",
    name="configuration_type",
    create_type=False,
)

CONFIGURATION_SCOPE_TYPE = SAEnum(
    "platform", "client", "institution",
    name="configuration_scope_type",
    create_type=False,
)

CONFIGURATION_CATEGORY = SAEnum(
    "Business Rules", "Display", "Academic", "Notifications",
    "Feature Toggles", "Platform", "Integrations",
    name="configuration_category",
    create_type=False,
)

CONFIGURATION_MERGE_STRATEGY = SAEnum(
    "replace", "append_lists", "deep_merge",
    name="configuration_merge_strategy",
    create_type=False,
)

CONFIGURATION_AUDIT_ACTION = SAEnum(
    "key_created", "key_updated", "key_deprecated",
    "value_created", "value_updated", "value_deleted",
    name="configuration_audit_action",
    create_type=False,
)


# ============================================================
# ConfigurationKey — registry of all named settings
# ============================================================
class ConfigurationKey(Base):
    """Registry of every key that exists on the platform.

    Platform-Owner-managed. No RLS (global registry, all roles can read).
    Default value is REQUIRED (per PRD D9).
    Soft delete via is_deprecated + deprecated_at (per PRD D13).
    """

    __tablename__ = "configuration_key"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    key: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(CONFIGURATION_TYPE, nullable=False)
    default_value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    merge_strategy: Mapped[str] = mapped_column(
        CONFIGURATION_MERGE_STRATEGY, nullable=False, server_default="replace",
    )
    category: Mapped[str] = mapped_column(CONFIGURATION_CATEGORY, nullable=False, index=True)
    module: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_feature_toggle: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )
    is_deprecated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), index=True,
    )
    deprecated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    replacement_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_values: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )

    # Relationships
    values: Mapped[list["ConfigurationValue"]] = relationship(
        "ConfigurationValue",
        back_populates="key_ref",
        cascade="all, delete-orphan",
    )
    audit_entries: Mapped[list["ConfigurationAudit"]] = relationship(
        "ConfigurationAudit",
        back_populates="key_ref",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ConfigurationKey {self.key} type={self.type} deprecated={self.is_deprecated}>"


# ============================================================
# ConfigurationValue — scope-bound override of a key
# ============================================================
class ConfigurationValue(Base):
    """Override of a key's value at a specific scope (Client or Institution).

    Platform-scope values are NOT stored as rows — the platform default lives
    on the key's default_value field (per PRD D43).

    RLS enforces tenant isolation (per PRD D42).
    """

    __tablename__ = "configuration_value"
    __table_args__ = (
        UniqueConstraint(
            "key_id", "scope_type", "scope_id",
            name="uq_configuration_value_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    key_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("configuration_key.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(CONFIGURATION_SCOPE_TYPE, nullable=False, index=True)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True, index=True,
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True, index=True,
    )
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True,
    )

    # Relationships
    key_ref: Mapped["ConfigurationKey"] = relationship("ConfigurationKey", back_populates="values")

    def __repr__(self) -> str:
        return f"<ConfigurationValue key_id={self.key_id} scope={self.scope_type}:{self.scope_id}>"


# ============================================================
# ConfigurationAudit — append-only change log
# ============================================================
class ConfigurationAudit(Base):
    """Append-only change log for key create/update/deprecate and value create/update/delete.

    Lightweight: who/what/when only. No before/after values stored (per PRD D6).
    Append-only enforced at the application layer; no UPDATE/DELETE in any code path.
    """

    __tablename__ = "configuration_audit"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    key_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("configuration_key.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str | None] = mapped_column(CONFIGURATION_SCOPE_TYPE, nullable=True)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(CONFIGURATION_AUDIT_ACTION, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True, index=True,
    )
    actor_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), index=True,
    )

    # Relationships
    key_ref: Mapped["ConfigurationKey"] = relationship(
        "ConfigurationKey", back_populates="audit_entries",
    )

    def __repr__(self) -> str:
        return f"<ConfigurationAudit {self.action} key_id={self.key_id} actor={self.actor_role}>"
