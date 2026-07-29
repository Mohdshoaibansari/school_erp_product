"""C-08 Configuration Framework — repository layer (sync).

All database access for ConfigurationKey, ConfigurationValue, ConfigurationAudit.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kernel.config.models.configuration_models import (
    ConfigurationAudit,
    ConfigurationKey,
    ConfigurationValue,
)

logger = logging.getLogger(__name__)


class ConfigurationRepository:
    """Sync repository for C-08 entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================
    # Key CRUD
    # ============================================================

    def list_keys(
        self,
        category: str | None = None,
        module: str | None = None,
        is_deprecated: bool | None = None,
        is_feature_toggle: bool | None = None,
        include_deprecated: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ConfigurationKey], int]:
        """List keys with optional filters. Returns (results, total_count)."""
        stmt = select(ConfigurationKey)
        conditions = []
        if category is not None:
            conditions.append(ConfigurationKey.category == category)
        if module is not None:
            conditions.append(ConfigurationKey.module == module)
        if is_deprecated is not None:
            conditions.append(ConfigurationKey.is_deprecated == is_deprecated)
        if is_feature_toggle is not None:
            conditions.append(ConfigurationKey.is_feature_toggle == is_feature_toggle)
        if not include_deprecated:
            threshold = datetime.now(timezone.utc) - timedelta(days=90)
            conditions.append(
                ~(ConfigurationKey.is_deprecated == True)  # noqa: E712
                | (ConfigurationKey.deprecated_at.is_(None))
                | (ConfigurationKey.deprecated_at > threshold)
            )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Count
        count_stmt = select(func.count()).select_from(ConfigurationKey)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = self.db.execute(count_stmt).scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = stmt.order_by(ConfigurationKey.key).offset(offset).limit(page_size)
        keys = list(self.db.execute(stmt).scalars().all())
        return keys, total

    def get_key_by_id(self, key_id: uuid.UUID) -> ConfigurationKey | None:
        return self.db.get(ConfigurationKey, key_id)

    def get_key_by_name(self, key_name: str) -> ConfigurationKey | None:
        stmt = select(ConfigurationKey).where(ConfigurationKey.key == key_name)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_key(
        self,
        key_name: str,
        key_type: str,
        default_value: Any,
        category: str,
        description: str,
        merge_strategy: str = "replace",
        module: str | None = None,
        is_feature_toggle: bool = False,
        allowed_values: Any | None = None,
    ) -> ConfigurationKey:
        if default_value is None:
            raise ValueError("default_value is required")
        k = ConfigurationKey(
            key=key_name,
            type=key_type,
            default_value=default_value,
            merge_strategy=merge_strategy,
            category=category,
            module=module,
            description=description,
            is_feature_toggle=is_feature_toggle,
            allowed_values=allowed_values,
        )
        self.db.add(k)
        try:
            self.db.flush()
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Key '{key_name}' already exists") from e
        return k

    def update_key(
        self,
        key_id: uuid.UUID,
        *,
        default_value: Any | None = None,
        description: str | None = None,
        merge_strategy: str | None = None,
        category: str | None = None,
        module: str | None = None,
        is_feature_toggle: bool | None = None,
        allowed_values: Any | None = None,
    ) -> ConfigurationKey | None:
        k = self.db.get(ConfigurationKey, key_id)
        if k is None:
            return None
        if default_value is not None:
            k.default_value = default_value
        if description is not None:
            k.description = description
        if merge_strategy is not None:
            k.merge_strategy = merge_strategy
        if category is not None:
            k.category = category
        if module is not None:
            k.module = module
        if is_feature_toggle is not None:
            k.is_feature_toggle = is_feature_toggle
        if allowed_values is not None:
            k.allowed_values = allowed_values
        self.db.flush()
        return k

    def soft_delete_key(
        self,
        key_id: uuid.UUID,
        replacement_key: str | None,
    ) -> ConfigurationKey | None:
        k = self.db.get(ConfigurationKey, key_id)
        if k is None:
            return None
        k.is_deprecated = True
        k.deprecated_at = datetime.now(timezone.utc)
        k.replacement_key = replacement_key
        self.db.flush()
        return k

    # ============================================================
    # Value CRUD
    # ============================================================

    def list_values(
        self,
        key_id: uuid.UUID | None = None,
        scope_type: str | None = None,
        scope_id: uuid.UUID | None = None,
        client_id: uuid.UUID | None = None,
        institution_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ConfigurationValue], int]:
        stmt = select(ConfigurationValue)
        conditions = []
        if key_id is not None:
            conditions.append(ConfigurationValue.key_id == key_id)
        if scope_type is not None:
            conditions.append(ConfigurationValue.scope_type == scope_type)
        if scope_id is not None:
            conditions.append(ConfigurationValue.scope_id == scope_id)
        if client_id is not None:
            conditions.append(ConfigurationValue.client_id == client_id)
        if institution_id is not None:
            conditions.append(ConfigurationValue.institution_id == institution_id)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        count_stmt = select(func.count()).select_from(ConfigurationValue)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = self.db.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.order_by(ConfigurationValue.key_id, ConfigurationValue.scope_type).offset(offset).limit(page_size)
        values = list(self.db.execute(stmt).scalars().all())
        return values, total

    def get_value(
        self,
        key_id: uuid.UUID,
        scope_type: str,
        scope_id: uuid.UUID | None,
    ) -> ConfigurationValue | None:
        stmt = select(ConfigurationValue).where(
            and_(
                ConfigurationValue.key_id == key_id,
                ConfigurationValue.scope_type == scope_type,
                ConfigurationValue.scope_id == scope_id,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_value_by_id(self, value_id: uuid.UUID) -> ConfigurationValue | None:
        return self.db.get(ConfigurationValue, value_id)

    def create_value(
        self,
        key_id: uuid.UUID,
        scope_type: str,
        scope_id: uuid.UUID,
        value: Any,
        client_id: uuid.UUID | None,
        institution_id: uuid.UUID | None,
        updated_by: uuid.UUID,
    ) -> ConfigurationValue:
        k = self.db.get(ConfigurationKey, key_id)
        if k is None:
            raise ValueError(f"Key {key_id} not found")
        if k.is_deprecated:
            raise ValueError(f"Key '{k.key}' is deprecated — cannot create new value overrides")
        _validate_value_type(value, k.type)

        v = ConfigurationValue(
            key_id=key_id,
            scope_type=scope_type,
            scope_id=scope_id,
            client_id=client_id,
            institution_id=institution_id,
            value=value,
            updated_by=updated_by,
        )
        self.db.add(v)
        try:
            self.db.flush()
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Duplicate value for key={key_id} scope={scope_type}:{scope_id}") from e
        return v

    def update_value(
        self,
        value_id: uuid.UUID,
        value: Any,
    ) -> ConfigurationValue | None:
        v = self.db.get(ConfigurationValue, value_id)
        if v is None:
            return None
        k = self.db.get(ConfigurationKey, v.key_id)
        if k is not None:
            _validate_value_type(value, k.type)
        v.value = value
        self.db.flush()
        return v

    def delete_value(self, value_id: uuid.UUID) -> bool:
        v = self.db.get(ConfigurationValue, value_id)
        if v is None:
            return False
        self.db.delete(v)
        self.db.flush()
        return True

    # ============================================================
    # Audit
    # ============================================================

    def list_audit(
        self,
        key_id: uuid.UUID | None = None,
        scope_type: str | None = None,
        scope_id: uuid.UUID | None = None,
        action: str | None = None,
        actor_user_id: uuid.UUID | None = None,
        from_ts: Any = None,
        to_ts: Any = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ConfigurationAudit], int]:
        stmt = select(ConfigurationAudit)
        conditions = []
        if key_id is not None:
            conditions.append(ConfigurationAudit.key_id == key_id)
        if scope_type is not None:
            conditions.append(ConfigurationAudit.scope_type == scope_type)
        if scope_id is not None:
            conditions.append(ConfigurationAudit.scope_id == scope_id)
        if action is not None:
            conditions.append(ConfigurationAudit.action == action)
        if actor_user_id is not None:
            conditions.append(ConfigurationAudit.actor_user_id == actor_user_id)
        if from_ts is not None:
            conditions.append(ConfigurationAudit.timestamp >= from_ts)
        if to_ts is not None:
            conditions.append(ConfigurationAudit.timestamp <= to_ts)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        count_stmt = select(func.count()).select_from(ConfigurationAudit)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = self.db.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.order_by(ConfigurationAudit.timestamp.desc()).offset(offset).limit(page_size)
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def write_audit(
        self,
        key_id: uuid.UUID,
        action: str,
        scope_type: str | None = None,
        scope_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str | None = None,
    ) -> ConfigurationAudit:
        a = ConfigurationAudit(
            key_id=key_id,
            scope_type=scope_type,
            scope_id=scope_id,
            action=action,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
        self.db.add(a)
        self.db.flush()
        return a

    def get_institution_client_id(self, institution_id: uuid.UUID) -> uuid.UUID | None:
        from sqlalchemy import text
        result = self.db.execute(
            text("SELECT client_id FROM institution WHERE id = :id"),
            {"id": str(institution_id)},
        )
        row = result.fetchone()
        return row[0] if row else None


# ============================================================
# Type validation
# ============================================================

def _validate_value_type(value: Any, declared_type: str) -> None:
    """Validate that a value matches the declared type."""
    if value is None:
        return
    if declared_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"Value must be a string, got {type(value).__name__}")
    elif declared_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"Value must be a number, got {type(value).__name__}")
    elif declared_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"Value must be a boolean, got {type(value).__name__}")
    elif declared_type == "json":
        if not isinstance(value, (dict, list, str, int, float, bool, type(None))):
            raise ValueError(f"Value must be valid JSON, got {type(value).__name__}")
    elif declared_type == "date":
        if not isinstance(value, str):
            raise ValueError(f"Date value must be a string, got {type(value).__name__}")
