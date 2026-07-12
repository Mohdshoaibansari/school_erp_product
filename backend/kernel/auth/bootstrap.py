"""Bootstrap CLI for creating the platform owner in Supabase Auth (D30).

Run once after `alembic upgrade` to create the platform owner's Supabase Auth
user. The migration inserts the `app_user` row; this CLI creates the matching
`auth.users` row.

Usage:
    uv run python -m kernel.auth.bootstrap
"""

from __future__ import annotations

import os
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session


def _get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
    )


def bootstrap_platform_owner() -> None:
    """Create the platform owner in Supabase Auth (D30).

    Looks up the platform owner `app_user` row. Calls Supabase Auth
    Admin API to create the matching user with the initial password.
    Idempotent — checks if Supabase user exists first.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    initial_password = os.environ.get("PLATFORM_OWNER_INITIAL_PASSWORD")

    if not supabase_url:
        print("ERROR: SUPABASE_URL environment variable is required")
        sys.exit(1)
    if not service_role_key:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY environment variable is required")
        sys.exit(1)
    if not initial_password:
        print("ERROR: PLATFORM_OWNER_INITIAL_PASSWORD environment variable is required")
        sys.exit(1)

    # Look up the platform owner app_user row
    engine = create_engine(_get_database_url())
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        result = session.execute(
            text("SELECT id, email FROM app_user WHERE lifecycle_status = 'active' AND name = 'Platform Owner' LIMIT 1")
        )
        row = result.fetchone()
        if not row:
            print("ERROR: Platform owner app_user row not found. Run migrations first.")
            sys.exit(1)

        platform_owner_id = row[0]
        platform_owner_email = row[1]

    # Create the Supabase Auth user
    from supabase import create_client
    client = create_client(supabase_url, service_role_key)

    try:
        # Check if user already exists in Supabase Auth
        try:
            existing = client.auth.admin.get_user_by_id(str(platform_owner_id))
            if existing and existing.user:
                print(f"Platform owner already exists in Supabase Auth: {platform_owner_email}")
                return
        except Exception:
            pass  # User doesn't exist, create them

        # Create the user
        response = client.auth.admin.create_user({
            "id": str(platform_owner_id),
            "email": platform_owner_email,
            "password": initial_password,
            "email_confirm": True,
        })
        print(f"Platform owner created in Supabase Auth: {platform_owner_email}")
    except Exception as e:
        print(f"ERROR: Failed to create platform owner: {e}")
        sys.exit(1)


if __name__ == "__main__":
    bootstrap_platform_owner()
