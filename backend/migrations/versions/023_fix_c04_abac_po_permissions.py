"""Fix C-04 ABAC — seed platform_owner platform permissions.

Platform Owner is now evaluated through the normal authorization pipeline
(no unconditional bypass, fix-c04-authz-abac-enforcement D4/D5). This
migration seeds the explicit ``role_permission`` rows the Platform Owner
needs for the platform surface (design D6): the exact resources/actions the
platform router references (``backend/business/tenant_institution/routes/
platform.py``). No wildcard and no hierarchy are introduced — every grant is
explicit.

Adds:
1. New ``permission`` row ``client.create`` (referenced by
   POST /api/v1/platform/clients; no row existed before).
2. ``role_permission`` rows at scope ``'any'`` for ``platform_owner``:
   client.create/read/update/transfer_ownership/transition_lifecycle,
   institution_type.read/create/update.
3. Re-seats ALL existing ``platform_owner`` ``role_permission`` rows
   (including the 8 ``config.*`` from migration 009, previously seeded with
   the 016 server-default ``'institution'``) to scope ``'any'`` —
   platform-level operations are not tenant-scoped.

Post-migration verification query (documented in design D6):

    SELECT r.name AS role, p.name AS permission, rp.scope
    FROM role_permission rp
    JOIN role r ON r.id = rp.role_id
    JOIN permission p ON p.id = rp.permission_id
    WHERE r.name = 'platform_owner'
    ORDER BY p.name;
    -- expect: client.* 5, institution_type.* 3, config.* 8 — all scope 'any'

Revision ID: 023_fix_c04_abac_po_permissions
Revises: 022_person_model_revamp
Create Date: 2025-01-01
"""

from alembic import op
import sqlalchemy as sa

revision = "023_fix_c04_abac_po_permissions"
down_revision = "022_person_model_revamp"
branch_labels = None
depends_on = None


# Explicit platform surface the platform_owner role needs (design D6, grounded
# in platform.py route require_permission calls). No wildcard, no hierarchy.
_PO_PLATFORM_PERMS = [
    "client.create",                      # NEW permission row; POST /api/v1/platform/clients
    "client.read",                        # GET  /api/v1/platform/clients[/{id}]
    "client.update",                      # PATCH /api/v1/platform/clients/{id}
    "client.transfer_ownership",          # POST /api/v1/platform/ownership-transfers
    "client.transition_lifecycle",        # POST /api/v1/platform/clients/{id}/transition
    "institution_type.read",              # GET  /api/v1/platform/institution-types[/{id}]
    "institution_type.create",            # POST /api/v1/platform/institution-types
    "institution_type.update",            # PATCH /api/v1/platform/institution-types/{id}
    # config.* (8, seeded in migration 009) — scope corrected to 'any' below
]


def upgrade() -> None:
    # 1. client.create — no permission row exists today (only the route requires it)
    op.execute(
        sa.text(
            "INSERT INTO permission (id, name, description, resource, action) "
            "VALUES (gen_random_uuid(), 'client.create', "
            "'Create a client (platform-level)', 'client', 'create') "
            "ON CONFLICT (name) DO NOTHING"
        )
    )

    # 2. Seed platform_owner rows at scope 'any' (explicit perms only)
    for perm in _PO_PLATFORM_PERMS:
        op.execute(
            sa.text(
                "INSERT INTO role_permission (id, role_id, permission_id, scope) "
                "SELECT gen_random_uuid(), r.id, p.id, 'any' "
                "FROM role r, permission p "
                f"WHERE r.name = 'platform_owner' AND p.name = '{perm}' "
                "ON CONFLICT (role_id, permission_id) DO NOTHING"
            )
        )

    # 3. Re-seat ALL platform_owner rows (incl. config.* from 009) to scope 'any'
    op.execute(
        sa.text(
            "UPDATE role_permission SET scope = 'any' "
            "WHERE role_id = (SELECT id FROM role WHERE name = 'platform_owner')"
        )
    )


def downgrade() -> None:
    # Remove the client.*/institution_type.* platform_owner rows seeded here
    op.execute(
        sa.text(
            "DELETE FROM role_permission WHERE role_id = "
            "(SELECT id FROM role WHERE name = 'platform_owner') "
            "AND permission_id IN (SELECT id FROM permission "
            "WHERE name IN ('client.create','client.read','client.update',"
            "'client.transfer_ownership','client.transition_lifecycle',"
            "'institution_type.read','institution_type.create','institution_type.update'))"
        )
    )
    # Delete the newly-created permission row
    op.execute(sa.text("DELETE FROM permission WHERE name = 'client.create'"))
    # Restore 009-era scope ('institution') for the config.* platform_owner rows
    op.execute(
        sa.text(
            "UPDATE role_permission SET scope = 'institution' WHERE role_id = "
            "(SELECT id FROM role WHERE name = 'platform_owner')"
        )
    )