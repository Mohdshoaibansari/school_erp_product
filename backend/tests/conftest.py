"""pytest fixtures for C-01 tests.

Session-scoped: ensures the local Supabase Postgres is available, resets the
schema, and applies Alembic migrations. Provides a synchronous DB engine and
session factory for tests.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Generator

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from kernel.app_factory import create_app
from business.tenant_institution.manifest import manifest as c01_manifest
from kernel.tenant_context import TenantContext, set_tenant_context
from kernel.middleware import mint_test_jwt
from business.tenant_institution.dependencies import reset_service_singleton
from kernel.audit import AuditEmitter, DefaultAuditEmitter

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
)

# Tables that hold seed data (should NOT be cleaned between tests)
_SEED_TABLES = {"legal_entity_type", "org_unit_type", "institution_type_name"}

# All C-01 entity tables in reverse dependency order for cleanup
_C01_TABLES = [
    "ownership_transfer_event",
    "institution_lifecycle_event",
    "client_lifecycle_event",
    "approval",
    "org_unit",
    "institution",
    "institution_type",
    "client",
]


def _ensure_supabase_running() -> None:
    """Ensure the local Supabase stack is running (start if needed)."""
    try:
        result = subprocess.run(
            ["supabase", "status"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            timeout=30,
        )
        if result.returncode != 0:
            subprocess.run(
                ["supabase", "start", "--ignore-health-check"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(__file__)),
                timeout=180,
            )
    except FileNotFoundError:
        pass  # Supabase CLI not available — assume DB is already running


def _reset_database() -> None:
    """Reset the database by dropping and recreating the public schema,
    then applying Alembic migrations from scratch.
    """
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Drop and recreate public schema to get a clean state
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        # Grant permissions (Supabase default)
        conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()
    engine.dispose()

    # Apply migrations from scratch
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
    )


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Session-scoped DB engine. Resets the database before the session."""
    _ensure_supabase_running()
    _reset_database()
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(db_engine: Engine) -> sessionmaker[Session]:
    """Session factory bound to the test engine."""
    return sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
def db_session(db_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Per-test DB session. Deletes all non-seed data after each test."""
    session = db_session_factory()
    yield session
    # Clean up all non-seed data so tests start from a clean state
    # (some RLS tests commit, so rollback alone is insufficient)
    session.rollback()
    # Set platform owner to bypass RLS during cleanup (FORCE RLS is on)
    session.execute(text("SET LOCAL app.is_platform_owner = 'true'"))
    for table_name in _C01_TABLES:
        session.execute(text(f"DELETE FROM {table_name}"))
    session.commit()
    session.close()


# ============================================================
# Apply-B fixtures: auth, tenant context, TestClient (7.1, 7.2)
# ============================================================

@pytest.fixture
def test_jwt():
    """Factory for minting Supabase-compatible test JWTs (tech-stack ADR §3).
    C-01 consumes JWTs; tests mint them with a test secret.
    """
    def _mint(
        *,
        user_id: str = "test-user",
        client_id: str | uuid.UUID | None = None,
        institution_id: str | uuid.UUID | None = None,
        is_platform_owner: bool = False,
        roles: list[str] | None = None,
    ) -> str:
        return mint_test_jwt(
            user_id=user_id,
            client_id=str(client_id) if client_id else None,
            institution_id=str(institution_id) if institution_id else None,
            is_platform_owner=is_platform_owner,
            roles=roles,
        )
    return _mint


@pytest.fixture
def tenant_context_override():
    """Override ``get_tenant_context`` with a fixed context for tests (7.2).

    Usage in a test:
        app = create_app([c01_manifest])
        app.dependency_overrides[get_tenant_context] = lambda: ctx
    """
    contexts = []

    def _set(ctx: TenantContext) -> TenantContext:
        contexts.append(ctx)
        set_tenant_context(ctx)
        return ctx

    yield _set

    # Reset the contextvar after the test
    set_tenant_context(None)


@pytest.fixture
def app():
    """Create a FastAPI app with the C-01 manifest (with middleware)."""
    reset_service_singleton()
    app = create_app([c01_manifest])
    yield app
    reset_service_singleton()


@pytest.fixture
def platform_client(app, test_jwt):
    """TestClient with a Platform Owner JWT (D11).
    Uses a platform Host (localhost) so the middleware treats it as platform-scoped.
    """
    token = test_jwt(is_platform_owner=True, user_id="platform-owner")
    client = TestClient(app, headers={
        "Authorization": f"Bearer {token}",
        "Host": "localhost",
    })
    return client


@pytest.fixture
def make_tenant_client(app, test_jwt):
    """Factory for creating a TestClient with a specific subdomain + JWT (7.1).

    Usage:
        client = make_tenant_client(subdomain="school-a", client_id=client_a_id)
    """
    def _make(
        *,
        subdomain: str,
        client_id: uuid.UUID,
        institution_id: uuid.UUID | None = None,
        is_platform_owner: bool = False,
        roles: list[str] | None = None,
        user_id: str = "test-user",
    ) -> TestClient:
        token = test_jwt(
            user_id=user_id,
            client_id=client_id,
            institution_id=institution_id,
            is_platform_owner=is_platform_owner,
            roles=roles or ["client_director"],
        )
        return TestClient(app, headers={
            "Authorization": f"Bearer {token}",
            "Host": f"{subdomain}.localhost",
        })
    return _make


# ============================================================
# Apply-D fixtures: audit emitter (13.x) + role contexts (12.x)
# ============================================================

@pytest.fixture
def audit_emitter() -> DefaultAuditEmitter:
    """Capture audit emitter for 13.x tests (records emitted events in a list)."""
    return DefaultAuditEmitter()


@pytest.fixture
def platform_owner_ctx():
    """Platform Owner TenantContext (D11 — ALL C-01 operations)."""
    return TenantContext(
        client_id=uuid.uuid4(),
        is_platform_owner=True,
        roles=["platform_owner"],
        user_id="platform-owner",
    )


@pytest.fixture
def client_director_ctx():
    """Client Director TenantContext (D11 — own-client scope)."""
    return TenantContext(
        client_id=uuid.uuid4(),
        is_platform_owner=False,
        roles=["client_director"],
        user_id="client-director",
    )


@pytest.fixture
def institution_admin_ctx():
    """Institution Admin TenantContext (D11 — own-institution scope)."""
    return TenantContext(
        client_id=uuid.uuid4(),
        institution_id=uuid.uuid4(),
        is_platform_owner=False,
        roles=["institution_admin"],
        user_id="institution-admin",
    )


@pytest.fixture
def cross_institution_role_ctx():
    """Cross-institution role TenantContext (D11 — READ-only on C-01)."""
    return TenantContext(
        client_id=uuid.uuid4(),
        is_platform_owner=False,
        roles=["regional_manager"],
        user_id="regional-manager",
    )
