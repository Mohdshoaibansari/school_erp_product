"""Bootstrap CLI for creating the platform owner in Supabase Auth (D30, task 13.1).

Run once after `alembic upgrade` to create the platform owner's Supabase Auth
user. The migration inserts the `app_user` row; this CLI creates the matching
`auth.users` row.

Usage:
    uv run python -m kernel.auth.bootstrap

Environment:
    SUPABASE_URL — Supabase project URL
    SUPABASE_SERVICE_ROLE_KEY — Supabase service-role key
    PLATFORM_OWNER_INITIAL_PASSWORD — initial password for platform owner
    DATABASE_URL — optional, defaults to local Supabase Postgres
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def _get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
    )


async def bootstrap_platform_owner() -> None:
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
        # PO discovery via is_platform_owner flag (T-26, D6a)
        # user_category table dropped; PO is identified by the role_assignment scope or is_platform_owner flag.
        result = session.execute(
            text(
                "SELECT au.id, au.email FROM app_user au "
                "JOIN role_assignment ra ON ra.user_id = au.id "
                "JOIN role r ON r.id = ra.role_id "
                "WHERE au.lifecycle_status = 'active' "
                "AND ra.scope = 'Platform' "
                "LIMIT 1"
            )
        )
        row = result.fetchone()
        if not row:
            # Fallback: try the first active app_user
            result = session.execute(
                text(
                    "SELECT id, email FROM app_user "
                    "WHERE lifecycle_status = 'active' "
                    "LIMIT 1"
                )
            )
            row = result.fetchone()
        if not row:
            print("ERROR: Platform owner app_user row not found. Run migrations first.")
            sys.exit(1)

        platform_owner_id = row[0]
        platform_owner_email = row[1]

    print(f"Found platform owner: {platform_owner_email} (id={platform_owner_id})")

    # Create SupabaseAuthClient and call Supabase
    from kernel.auth.supabase_client import SupabaseAuthClientImpl, SupabaseAuthError

    client = SupabaseAuthClientImpl(supabase_url, service_role_key)

    try:
        # Check if user already exists in Supabase Auth
        # Use sign_in_with_password as existence check (update_user fails with "User not allowed")
        try:
            existing = await client.sign_in_with_password(platform_owner_email, initial_password)
            if existing and existing.get("access_token"):
                print(f"Platform owner already exists in Supabase Auth: {platform_owner_email}")
                return
        except SupabaseAuthError:
            pass  # User doesn't exist or password wrong, create them

        # Create the user WITH password (D11)
        await client.create_user(platform_owner_id, platform_owner_email, password=initial_password)
        print(f"Platform owner created in Supabase Auth: {platform_owner_email}")
    except SupabaseAuthError as e:
        print(f"ERROR: Failed to create platform owner: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(bootstrap_platform_owner())
