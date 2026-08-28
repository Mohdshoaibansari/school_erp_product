"""C-04 Authorization — policy loader (D9, D11, D24, D29, AC-12, AC-13).

At startup, reads ``role_permission`` from the database and stores the
mapping in an in-memory dict.  ``register_policies_from_map`` then pushes
the policies into the Casbin enforcer via ``register_casbin_policies``.

Extended for ABAC (D9):
- Two catalogs: ``_non_conditional`` (from DB) and ``_conditional`` (code-driven).
- ``register_conditional_policy`` for attribute-conditional policies.
- Catalog query helpers: ``required_attributes``, ``has_permission``, ``matching_scopes``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

# In-memory permission map: {role_name: [(resource, action, scope), ...]}
_permission_map: dict[str, list[tuple[str, str, str]]] = {}

# Policy catalog — two tiers (D9)
# Non-conditional: from role_permission DB, unchanged source
_non_conditional: dict[str, list[tuple[str, str, str]]] = {}
# Conditional: code-driven, this enhancement
_conditional: dict[str, list[tuple[str, str, str, str]]] = {}


def _get_session() -> Session:
    """Create a SQLAlchemy session from the DATABASE_URL env var."""
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
    )
    engine = create_engine(database_url)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def load_permission_map() -> None:
    """Read all role_permission rows and populate the in-memory map (D24, 6.1).

    Reads ``role_permission`` joined with ``role`` and ``permission``.
    Stores into ``_permission_map`` keyed by role name.
    """
    global _permission_map
    session = _get_session()
    try:
        rows = session.execute(text("""
            SELECT r.name AS role_name, p.resource, p.action, rp.scope
            FROM role_permission rp
            JOIN role r ON r.id = rp.role_id
            JOIN permission p ON p.id = rp.permission_id
            ORDER BY r.name, p.resource, p.action
        """)).fetchall()

        _permission_map.clear()
        for role_name, resource, action, scope in rows:
            _permission_map.setdefault(role_name, []).append((resource, action, scope))

        logger.info(
            "C-04 policy loader: loaded %d role-permission mappings across %d roles",
            len(rows), len(_permission_map),
        )
    finally:
        session.close()


def register_policies_from_map(enforcer: Any) -> None:
    """Push the in-memory permission map into the Casbin enforcer (D24, 6.2).

    For each role → (resource, action) pair, adds a Casbin policy with
    ``institution`` scope and a role grouping policy. Policies are registered
    as 5-arg (with empty attrs) for the extended model (D9).

    Also populates ``_non_conditional`` catalog.

    Called by ``register_casbin_policies(enforcer)`` in the manifest.
    """
    _non_conditional.clear()

    for role_name, permissions in _permission_map.items():
        # Casbin role hierarchy: the identity role label is also a Casbin role
        enforcer.add_role_for_user(role_name, role_name)

        for resource, action, scope in permissions:
            # 5-arg policy with empty attrs for non-conditional policies (D9)
            enforcer.add_policy(role_name, resource, action, scope, "")
            _non_conditional.setdefault(role_name, []).append((resource, action, scope))

    logger.info(
        "C-04 policy loader: registered %d role mappings into enforcer (5-arg)",
        len(_permission_map),
    )


def register_conditional_policy(
    enforcer: Any,
    role: str,
    resource: str,
    action: str,
    scope: str,
    required_attrs: Sequence[str],
) -> None:
    """Declare a code-driven conditional policy (D9, REQ-AUTHZ-ABAC-M04).

    Adds to both the Casbin enforcer and the in-memory conditional catalog.

    Args:
        enforcer: The Casbin enforcer instance.
        role: Role name (e.g., "Teacher").
        resource: Resource type (e.g., "homework").
        action: Action (e.g., "create").
        scope: Scope (e.g., "institution").
        required_attrs: Sequence of required attribute names (e.g., ["is_subject_teacher"]).
    """
    attrs_str = ",".join(required_attrs)
    enforcer.add_policy(role, resource, action, scope, attrs_str)
    _conditional.setdefault(role, []).append((resource, action, scope, attrs_str))
    logger.debug(
        "Registered conditional policy: (%s, %s, %s, %s, %s)",
        role, resource, action, scope, attrs_str,
    )


def required_attributes(roles: list[str], resource: str, action: str) -> set[str]:
    """Return the union of required attributes across all conditional entries
    matching any role × (resource, action) (D9, REQ-AUTHZ-ABAC-02).

    Used by AuthorizationService to determine which attributes to resolve.

    Note (D10, deferred optimization): the union spans ALL subject roles; it is a
    superset of what any single role needs. This is conservative but not a bug —
    an extra resolver call (and a possible fail-closed bias if that extra
    attribute has no provider). Re-scoping to only the roles that hold a matching
    policy is deferred until Phase 7 introduces real production conditional
    policies to validate against.
    """
    attrs: set[str] = set()
    for role in roles:
        for res, act, _scope, attrs_str in _conditional.get(role, []):
            if res == resource and act == action:
                if attrs_str:
                    attrs.update(attrs_str.split(","))
    return attrs


def has_permission(roles: list[str], resource: str, action: str) -> bool:
    """Return True if any role has (resource, action) in either catalog (D9).

    Used by _classify_denial to determine MISSING_PERMISSION vs scope/attr issues.
    """
    for role in roles:
        # Check non-conditional catalog
        for res, act, _scope in _non_conditional.get(role, []):
            if res == resource and act == action:
                return True
        # Check conditional catalog
        for res, act, _scope, _attrs in _conditional.get(role, []):
            if res == resource and act == action:
                return True
    return False


def matching_scopes(
    roles: list[str],
    resource: str,
    action: str,
    sub_client: Any,
    sub_inst: Any,
    obj_client: Any,
    obj_inst: Any,
) -> list[str]:
    """Return the scopes that match the permission and whose tenant/institution
    constraints hold (D9).

    Used by _classify_denial to determine the specific scope violation.
    Never grants — Casbin is the sole granter.
    """
    scopes: list[str] = []
    sub_client_str = str(sub_client or "")
    sub_inst_str = str(sub_inst or "")
    obj_client_str = str(obj_client or "")
    obj_inst_str = str(obj_inst or "")

    for role in roles:
        # Check both catalogs
        all_entries = [
            (res, act, scope) for res, act, scope in _non_conditional.get(role, [])
        ] + [
            (res, act, scope) for res, act, scope, _attrs in _conditional.get(role, [])
        ]

        for res, act, scope in all_entries:
            if res != resource or act != action:
                continue

            # Check scope constraints
            if scope == "any":
                scopes.append(scope)
            elif scope == "tenant":
                if sub_client_str and obj_client_str and sub_client_str == obj_client_str:
                    scopes.append(scope)
            elif scope == "institution":
                if (sub_client_str and obj_client_str and sub_client_str == obj_client_str
                        and sub_inst_str and obj_inst_str and sub_inst_str == obj_inst_str):
                    scopes.append(scope)

    return scopes


def get_permission_map() -> dict[str, list[tuple[str, str, str]]]:
    """Return the current in-memory permission map (test helper)."""
    return dict(_permission_map)
