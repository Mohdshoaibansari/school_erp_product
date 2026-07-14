"""C-04 Authorization — policy loader (D11, D24, D29, AC-12, AC-13).

At startup, reads ``role_permission`` from the database and stores the
mapping in an in-memory dict.  ``register_policies_from_map`` then pushes
the policies into the Casbin enforcer via ``register_casbin_policies``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

# In-memory permission map: {role_name: [(resource, action), ...]}
_permission_map: dict[str, list[tuple[str, str]]] = {}


def _get_session() -> Session:
    """Create a SQLAlchemy session from the DATABASE_URL env var."""
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
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
            SELECT r.name AS role_name, p.resource, p.action
            FROM role_permission rp
            JOIN role r ON r.id = rp.role_id
            JOIN permission p ON p.id = rp.permission_id
            ORDER BY r.name, p.resource, p.action
        """)).fetchall()

        _permission_map.clear()
        for role_name, resource, action in rows:
            _permission_map.setdefault(role_name, []).append((resource, action))

        logger.info(
            "C-04 policy loader: loaded %d role-permission mappings across %d roles",
            len(rows), len(_permission_map),
        )
    finally:
        session.close()


def register_policies_from_map(enforcer: Any) -> None:
    """Push the in-memory permission map into the Casbin enforcer (D24, 6.2).

    For each role → (resource, action) pair, adds a Casbin policy with
    ``institution`` scope and a role grouping policy.

    Called by ``register_casbin_policies(enforcer)`` in the manifest.
    """
    for role_name, permissions in _permission_map.items():
        # Casbin role hierarchy: the identity role label is also a Casbin role
        enforcer.add_role_for_user(role_name, role_name)

        for resource, action in permissions:
            enforcer.add_policy(role_name, resource, action, "institution")

    logger.info(
        "C-04 policy loader: registered %d role mappings into enforcer",
        len(_permission_map),
    )


def get_permission_map() -> dict[str, list[tuple[str, str]]]:
    """Return the current in-memory permission map (test helper)."""
    return dict(_permission_map)
