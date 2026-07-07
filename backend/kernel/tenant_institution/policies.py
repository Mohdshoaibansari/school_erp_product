"""C-01 D11 permission-matrix policies for Casbin (12.1, AC-15, A5).

C-04 owns the Casbin framework; C-01 supplies the D11 tiered-delegation
matrix content and registers its own policies via the manifest
``register_casbin_policies(enforcer)`` hook (A5). This module holds the
matrix definition (role hierarchy + role/object/action policies) so the
manifest hook and tests share a single source of truth.

The matrix encodes D11:
- Platform Owner: ALL C-01 operations, any scope (cross-tenant included).
- Client Director (own-client): institution CRUD/lifecycle, Client+Institution
  identity update, OrgUnit management within their own client. CANNOT
  create/suspend/terminate the Client itself (Platform-gated).
- Institution Admin (own-institution): OrgUnit management + Institution identity
  within their own institution. CANNOT create/suspend/archive the Institution.
- Cross-institution roles (Regional Manager, Group Academic Head, Finance
  Controller): READ-only oversight on C-01 within their own client.

Own-client / own-institution scoping is ABAC: the subject's ``client_id`` /
``institution_id`` must match the requested object's (D11). Cross-tenant
reference architecture writes (Client create/suspend/terminate, ownership transfer) are
Platform-gated — only the Platform Owner has the ``any``-scope wildcard (12.2).
"""

from __future__ import annotations

import os
from typing import Any

# Role labels (D11)
ROLE_PLATFORM_OWNER = "platform_owner"
ROLE_CLIENT_DIRECTOR = "client_director"
ROLE_INSTITUTION_ADMIN = "institution_admin"
ROLE_CROSS_INSTITUTION = "cross_institution"

# Cross-institution oversight roles → mapped to the READ-only cross-institution tier
CROSS_INSTITUTION_ROLES = (
    "regional_manager",
    "group_academic_head",
    "finance_controller",
)

# Role hierarchy (Platform Owner is higher authority → inherits lower tiers, D11)
ROLE_HIERARCHY = [
    (ROLE_PLATFORM_OWNER, ROLE_CLIENT_DIRECTOR),
    (ROLE_PLATFORM_OWNER, ROLE_INSTITUTION_ADMIN),
    (ROLE_PLATFORM_OWNER, ROLE_CROSS_INSTITUTION),
    # Cross-institution oversight roles → cross_institution tier (READ-only)
    ("regional_manager", ROLE_CROSS_INSTITUTION),
    ("group_academic_head", ROLE_CROSS_INSTITUTION),
    ("finance_controller", ROLE_CROSS_INSTITUTION),
]

# Permission policies: (role, object, action, scope)
# scope = "any" (no tenant check) | "tenant" (own-client) | "institution" (own-institution)
PERMISSION_POLICIES: list[tuple[str, str, str, str]] = [
    # ---- Platform Owner: ALL operations, any scope (cross-tenant incl.) ----
    (ROLE_PLATFORM_OWNER, "*", "*", "any"),

    # ---- Client Director: own-client scope (tenant) ----
    (ROLE_CLIENT_DIRECTOR, "institution", "create", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "institution", "update_identity", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "institution", "transition", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "institution", "archive", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "institution", "read", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "client", "update_identity", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "client", "read", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "org_unit", "create", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "org_unit", "move", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "org_unit", "archive", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "org_unit", "reactivate", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "org_unit", "update_identity", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "org_unit", "reorder", "tenant"),
    (ROLE_CLIENT_DIRECTOR, "org_unit", "read", "tenant"),

    # ---- Institution Admin: own-institution scope ----
    (ROLE_INSTITUTION_ADMIN, "org_unit", "create", "institution"),
    (ROLE_INSTITUTION_ADMIN, "org_unit", "move", "institution"),
    (ROLE_INSTITUTION_ADMIN, "org_unit", "archive", "institution"),
    (ROLE_INSTITUTION_ADMIN, "org_unit", "reactivate", "institution"),
    (ROLE_INSTITUTION_ADMIN, "org_unit", "update_identity", "institution"),
    (ROLE_INSTITUTION_ADMIN, "org_unit", "reorder", "institution"),
    (ROLE_INSTITUTION_ADMIN, "org_unit", "read", "institution"),
    (ROLE_INSTITUTION_ADMIN, "institution", "update_identity", "institution"),
    (ROLE_INSTITUTION_ADMIN, "institution", "read", "institution"),

    # ---- Cross-institution roles: READ-only, own-client (tenant) ----
    (ROLE_CROSS_INSTITUTION, "client", "read", "tenant"),
    (ROLE_CROSS_INSTITUTION, "institution", "read", "tenant"),
    (ROLE_CROSS_INSTITUTION, "org_unit", "read", "tenant"),
]


def casbin_model_path() -> str:
    """Absolute path to the C-01 Casbin model file."""
    return os.path.join(os.path.dirname(__file__), "casbin_model.conf")


def register_policies(enforcer: Any) -> None:
    """Register the D11 matrix (role hierarchy + policies) onto a Casbin enforcer.

    Called by the manifest ``register_casbin_policies`` hook (A5). C-04 creates
    the enforcer with this model and invokes the hook; this function adds the
    role hierarchy links (g) and the permission policies (p). Idempotent for
    the same enforcer (add_policy / add_role_for_user skip existing links).
    """
    # Role hierarchy (g)
    for name, role in ROLE_HIERARCHY:
        enforcer.add_role_for_user(name, role)

    # Permission policies (p)
    for sub, obj, act, scope in PERMISSION_POLICIES:
        enforcer.add_policy(sub, obj, act, scope)


def build_enforcer():
    """Build a Casbin enforcer with the C-01 model + D11 policies (test helper).

    C-04 will own enforcer creation at app startup; this helper lets tests (and
    the future app-factory wiring) obtain a fully-registered C-01 enforcer
    without depending on C-04.
    """
    import casbin

    enforcer = casbin.Enforcer(casbin_model_path())
    register_policies(enforcer)
    return enforcer


def make_subject(role: str, client_id: str | None = None, institution_id: str | None = None):
    """Build a Casbin subject with D11 attributes (RBAC role + ABAC tenant ids)."""
    from types import SimpleNamespace

    return SimpleNamespace(
        role=role, client_id=client_id, institution_id=institution_id,
    )


def make_resource(name: str, client_id: str | None = None, institution_id: str | None = None):
    """Build a Casbin resource with the object name + D11 tenant ids."""
    from types import SimpleNamespace

    return SimpleNamespace(
        name=name, client_id=client_id, institution_id=institution_id,
    )