"""C-08 Configuration Framework — in-memory cache + resolution API.

This is the heart of C-08. On app startup, all ConfigurationKey and
ConfigurationValue rows are loaded into in-memory dicts. config.get() walks
the scope chain institution → client → platform, applies the merge strategy,
and returns the resolved value. O(1) lookups, zero DB hit on read.

Per PRD §6.4 (FR-21 to FR-24) and Design Decision 1.

The module-level singleton `config` is the public API entry point:
    from kernel.config.resolver import config
    value = config.get("attendance.markingCutoffTime", institution_id=inst_id)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import select

from kernel.db import get_session_factory

logger = logging.getLogger(__name__)


# Type aliases for the merge strategies
MergeStrategy = Literal["replace", "append_lists", "deep_merge"]
ValueType = Literal["string", "number", "boolean", "json", "date"]


# ============================================================
# Pure functions — merge logic and resolution
# ============================================================

def apply_merge(
    parent_value: Any,
    child_value: Any,
    merge_strategy: MergeStrategy,
    value_type: ValueType,
) -> Any:
    """Apply the merge strategy to combine parent + child values.

    Per PRD §6.3 (FR-16 to FR-19):
    - Scalars (string, number, boolean, date) ALWAYS use replace.
    - replace: child fully replaces parent.
    - append_lists: list values unioned with set semantics (order preserved).
    - deep_merge: JSON objects deep-merged per RFC 7396; lists replaced.

    Returns the resolved value.
    """
    # Scalars always replace (per FR-19)
    if value_type in ("string", "number", "boolean", "date"):
        return child_value

    # JSON type — apply the merge strategy
    if value_type == "json":
        if merge_strategy == "replace":
            return child_value
        elif merge_strategy == "append_lists":
            return _append_lists(parent_value, child_value)
        elif merge_strategy == "deep_merge":
            return _deep_merge(parent_value, child_value)
        else:
            logger.warning("Unknown merge_strategy '%s' — falling back to replace", merge_strategy)
            return child_value

    # Should not reach here
    return child_value


def _append_lists(parent: Any, child: Any) -> Any:
    """Union two list values with set semantics, preserving parent's order.

    If parent or child is not a list, return child (replace semantics).
    """
    if not isinstance(parent, list) or not isinstance(child, list):
        return child
    seen = set()
    result = []
    for item in parent + child:
        # Use repr as the hashable key for set semantics
        key = repr(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _deep_merge(parent: Any, child: Any) -> Any:
    """Deep-merge two JSON values per RFC 7396.

    - Objects (dicts): deep-merged, child values override parent.
    - Lists: child replaces parent.
    - Scalars: child replaces parent.
    """
    if not isinstance(parent, dict) or not isinstance(child, dict):
        return child
    result = dict(parent)
    for key, value in child.items():
        if key in result:
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ============================================================
# In-memory cache and resolution
# ============================================================

class ConfigurationCache:
    """In-memory cache of all keys and values, plus the resolution API.

    On app startup, `load_all_async()` populates the cache. On any UPDATE,
    the application code (in the service layer) calls `add_value`,
    `update_value`, `remove_value` etc. to patch the cache in-process.
    For multi-instance deployments, the NOTIFY listener also calls these
    methods on receipt of a `config_changes` event.
    """

    def __init__(self) -> None:
        # key_id (UUID str) -> ConfigurationKey
        self._keys_by_id: dict[str, Any] = {}
        # key (TEXT) -> ConfigurationKey
        self._keys_by_name: dict[str, Any] = {}
        # (scope_type, scope_id, key_id) -> ConfigurationValue
        self._values: dict[tuple[str, str | None, str], Any] = {}
        # Auto-hide threshold — defaults to 90 days, can be overridden by platform.configDeprecatedHideDays
        self._auto_hide_threshold_days = 90
        self._auto_hide_threshold = timedelta(days=90)
        self._loaded = False

    # -- Load from DB --

    def load_all(self) -> None:
        """Load all keys and values from the database into the in-memory dicts."""
        from kernel.config.models.configuration_models import (
            ConfigurationKey, ConfigurationValue,
        )

        session_factory = get_session_factory()
        with session_factory() as db:
            keys = list(db.execute(select(ConfigurationKey)).scalars().all())
            for k in keys:
                self._keys_by_id[str(k.id)] = k
                self._keys_by_name[k.key] = k

            values = list(db.execute(select(ConfigurationValue)).scalars().all())
            for v in values:
                key = (v.scope_type, str(v.scope_id) if v.scope_id else None, str(v.key_id))
                self._values[key] = v

        self._loaded = True
        logger.info(
            "[C-08 cache] Loaded %d keys and %d values into in-memory cache",
            len(self._keys_by_id), len(self._values),
        )

    # -- Cache patching methods (called from service layer + NOTIFY listener) --

    def add_key(self, key: Any) -> None:
        self._keys_by_id[str(key.id)] = key
        self._keys_by_name[key.key] = key

    def update_key(self, key: Any) -> None:
        self._keys_by_id[str(key.id)] = key
        self._keys_by_name[key.key] = key

    def remove_key(self, key_id: str) -> None:
        k = self._keys_by_id.pop(key_id, None)
        if k is not None:
            self._keys_by_name.pop(k.key, None)

    def add_value(self, value: Any) -> None:
        key = (value.scope_type, str(value.scope_id) if value.scope_id else None, str(value.key_id))
        self._values[key] = value

    def update_value(self, value: Any) -> None:
        key = (value.scope_type, str(value.scope_id) if value.scope_id else None, str(value.key_id))
        self._values[key] = value

    def remove_value(self, scope_type: str, scope_id: str | None, key_id: str) -> None:
        key = (scope_type, scope_id, key_id)
        self._values.pop(key, None)

    # -- Lookups --

    def get_key_by_name(self, name: str) -> Any | None:
        return self._keys_by_name.get(name)

    def get_key_by_id(self, key_id: str) -> Any | None:
        return self._keys_by_id.get(key_id)

    def get_value(self, key_id: str, scope_type: str, scope_id: str | None) -> Any | None:
        return self._values.get((scope_type, scope_id, key_id))

    def _get_value_internal(self, key_name: str) -> Any | None:
        """Get the platform default value for a key by name (no scope walk).
        Used internally by the cache itself for config-driven behavior.
        """
        k = self._keys_by_name.get(key_name)
        if k is None:
            return None
        return k.default_value

    def list_keys_for_filter(
        self,
        category: str | None = None,
        module: str | None = None,
        is_deprecated: bool | None = None,
        is_feature_toggle: bool | None = None,
        include_deprecated: bool = False,
    ) -> list[Any]:
        """List keys with optional filters. Applies 90-day auto-hide."""
        now = datetime.now(timezone.utc)
        results = []
        for k in self._keys_by_id.values():
            if category is not None and k.category != category:
                continue
            if module is not None and k.module != module:
                continue
            if is_deprecated is not None and k.is_deprecated != is_deprecated:
                continue
            if is_feature_toggle is not None and k.is_feature_toggle != is_feature_toggle:
                continue
            # Auto-hide: deprecated keys older than threshold are hidden
            if not include_deprecated and k.is_deprecated:
                # Dynamic threshold from platform.configDeprecatedHideDays
                threshold_val = self._get_value_internal('platform.configDeprecatedHideDays')
                threshold_days = int(threshold_val) if threshold_val else 90
                threshold = timedelta(days=threshold_days)
                if k.deprecated_at and (now - k.deprecated_at) > threshold:
                    continue
            results.append(k)
        return results

    def is_loaded(self) -> bool:
        return self._loaded


# ============================================================
# Resolution API
# ============================================================

class _ConfigAPI:
    """Public API surface for `config.get(...)` calls.

    Wraps the cache and applies scope walking + merge strategies.
    """

    def __init__(self) -> None:
        self._cache = ConfigurationCache()

    @property
    def cache(self) -> ConfigurationCache:
        return self._cache

    def load_all(self) -> None:
        self._cache.load_all()

    def get(
        self,
        key_name: str,
        institution_id: str | None = None,
        client_id: str | None = None,
    ) -> Any:
        """Resolve a config key for the given scope.

        Walks: institution → client → platform. Returns the first match.
        Falls back to the key's default_value if no override exists.

        Args:
            key_name: the dotted key name (e.g., "attendance.markingCutoffTime")
            institution_id: optional UUID string of the institution
            client_id: optional UUID string of the client

        Returns:
            The resolved value. Type matches the key's declared type.

        Raises:
            KeyError: if the key is not in the registry.
        """
        key = self._cache.get_key_by_name(key_name)
        if key is None:
            raise KeyError(f"Configuration key not found: {key_name}")

        key_id = str(key.id)
        value_type = key.type
        merge_strategy = key.merge_strategy

        # Walk the scope chain
        # 1. Institution scope
        if institution_id:
            v = self._cache.get_value(key_id, "institution", str(institution_id))
            if v is not None:
                return v.value
            # 2. Client scope
        if client_id:
            v = self._cache.get_value(key_id, "client", str(client_id))
            if v is not None:
                # If institution also has a value, apply merge
                if institution_id:
                    inst_v = self._cache.get_value(key_id, "institution", str(institution_id))
                    if inst_v is not None:
                        return apply_merge(v.value, inst_v.value, merge_strategy, value_type)
                return v.value
        # 3. Platform default (on the key itself)
        return key.default_value

    def get_with_source(
        self,
        key_name: str,
        institution_id: str | None = None,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        """Resolve a key AND return the source scope label.

        Used by the resolve debug endpoint.
        """
        key = self._cache.get_key_by_name(key_name)
        if key is None:
            raise KeyError(f"Configuration key not found: {key_name}")

        key_id = str(key.id)
        value_type = key.type
        merge_strategy = key.merge_strategy

        if institution_id:
            v = self._cache.get_value(key_id, "institution", str(institution_id))
            if v is not None:
                return {
                    "key": key_name,
                    "resolved_value": v.value,
                    "source_scope": f"institution:{institution_id}",
                }
        if client_id:
            v = self._cache.get_value(key_id, "client", str(client_id))
            if v is not None:
                return {
                    "key": key_name,
                    "resolved_value": v.value,
                    "source_scope": f"client:{client_id}",
                }
        return {
            "key": key_name,
            "resolved_value": key.default_value,
            "source_scope": "platform:default",
        }


# Module-level singleton — the public API
config = _ConfigAPI()
