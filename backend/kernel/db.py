"""SQLAlchemy 2.0 declarative base + engine setup for all platform models."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models (SQLAlchemy 2.0 style)."""
    pass


# ============================================================
# Engine setup
# ============================================================

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


_rls_hook_registered = False


def _register_rls_hook() -> None:
    """Register a SQLAlchemy Session 'before_transaction_create' event listener
    that sets RLS session variables from the current TenantContext on every new
    transaction.

    Per D5-a: uses Session-level event (not engine "connect") to ensure
    pooled connections reused for subsequent requests fire the hook fresh.
    The hook reads _tenant_context_var at fire-time and is contextvar-fresh.
    When _tenant_context_var.get() returns None (CLI, migration, early startup,
    unauthenticated flows), the hook returns without setting any variables.
    """
    global _rls_hook_registered
    if _rls_hook_registered:
        return
    _rls_hook_registered = True

    @event.listens_for(Session, "after_begin")
    def _set_rls_vars(session, transaction, connection):
        # Lazy-import the contextvar at fire-time (avoids circular imports)
        from kernel.tenant_context import _tenant_context_var

        ctx = _tenant_context_var.get()
        if ctx is None:
            return

        # Build SET LOCAL statements for each RLS session variable
        # app.is_platform_owner
        is_po = "true" if ctx.is_platform_owner else "false"
        connection.execute(text(f"SET LOCAL app.is_platform_owner = '{is_po}'"))

        # app.current_client_id
        if ctx.client_id is not None:
            connection.execute(text(f"SET LOCAL app.current_client_id = '{ctx.client_id}'"))

        # app.current_institution_id (D10 bug #3)
        if ctx.institution_id is not None:
            connection.execute(text(f"SET LOCAL app.current_institution_id = '{ctx.institution_id}'"))

        # app.current_user_id (D5 bug fix 3)
        if ctx.user_id is not None:
            connection.execute(text(f"SET LOCAL app.current_user_id = '{ctx.user_id}'"))


def set_rls_session_vars(
    session,
    *,
    user_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
    is_platform_owner: bool = False,
) -> None:
    """Set RLS session variables explicitly on a session.

    Use this for bootstrap flows where the middleware's TenantContext is
    incomplete (e.g., activate where the user is not yet authenticated).

    The service is responsible for verifying the values before calling this
    function. For activate, the user_id comes from a cryptographically signed
    invite token. The client_id and institution_id come from a DB lookup.

    Each SET LOCAL applies to the current transaction only.
    """
    if is_platform_owner:
        session.execute(text("SET LOCAL app.is_platform_owner = 'true'"))
    if user_id is not None:
        session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    if client_id is not None:
        session.execute(text(f"SET LOCAL app.current_client_id = '{client_id}'"))
    if institution_id is not None:
        session.execute(text(f"SET LOCAL app.current_institution_id = '{institution_id}'"))


def get_engine() -> Engine:
    """Get the global sync engine. Created lazily on first use."""
    global _engine
    if _engine is None:
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
        )
        _engine = create_engine(database_url, pool_pre_ping=True)
        logger.info("Created sync DB engine")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get the global sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
        _register_rls_hook()
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a Session, close on completion."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
