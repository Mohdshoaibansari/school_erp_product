"""Alembic environment configuration (A7 — single Alembic env, module-prefixed files).

Uses DATABASE_URL from the environment. Imports all model modules so
``alembic --autogenerate`` can detect schema changes. RLS policies are raw SQL
inside migration files (tech-stack ADR §3).
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the backend/ directory is on sys.path so ``kernel`` is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env file if present (same pattern as seed_data.py)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key, _val)

from kernel.db import Base  # noqa: E402

# Import all model modules so they register with Base.metadata
from business.tenant_institution import models  # noqa: E402, F401
from kernel.user import models as user_models  # noqa: E402, F401
from kernel.auth import models as auth_models  # noqa: E402, F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use DATABASE_URL from env, fallback to local Supabase
database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
)
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
