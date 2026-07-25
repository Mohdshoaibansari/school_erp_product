"""One-time migration: Move platform owner from app_user to Supabase Auth only.

What this script does:
1. Delete existing platform owner (platform@test-school.com) from role_assignment + app_user
2. Create new Supabase Auth user (admin@school-erp.com) with user_metadata.is_platform_owner = true

Usage:
    cd backend
    uv run python scripts/migrate_platform_owner.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text as sa_text
from sqlalchemy.orm import sessionmaker

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Load .env file
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if ENV_PATH.exists():
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# New platform owner credentials (D27, D28)
PLATFORM_EMAIL = "admin@school-erp.com"
PLATFORM_PASSWORD = "Shoby@123"


async def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    print("\n" + "=" * 60)
    print("PLATFORM OWNER MIGRATION")
    print("=" * 60 + "\n")

    # Step 1: Delete existing platform owner from app_user + role_assignment
    with Session() as s:
        # Find platform owner by email
        result = s.execute(
            sa_text("SELECT id FROM app_user WHERE email = :email"),
            {"email": "platform@test-school.com"},
        ).fetchone()

        if result:
            user_id = result[0]
            print(f"  Found platform owner: id={user_id}")

            # Delete related records (cascade order — FKs first)
            s.execute(sa_text("DELETE FROM login_attempt WHERE user_id = :uid"), {"uid": user_id})
            s.execute(sa_text("DELETE FROM role_assignment WHERE user_id = :uid"), {"uid": user_id})
            s.execute(sa_text("DELETE FROM user_identifier WHERE user_id = :uid"), {"uid": user_id})
            s.execute(sa_text("DELETE FROM user_profile WHERE user_id = :uid"), {"uid": user_id})
            s.execute(sa_text("DELETE FROM user_lifecycle_event WHERE user_id = :uid"), {"uid": user_id})
            s.execute(
                sa_text("DELETE FROM app_user WHERE id = :uid"),
                {"uid": user_id},
            )
            s.commit()
            print(f"  [OK] Deleted platform owner from app_user + related tables: id={user_id}")
        else:
            print("  [SKIP] No existing platform owner found (already migrated)")

    # Step 2: Create new platform owner in Supabase Auth
    print(f"\n  Creating platform owner in Supabase Auth: {PLATFORM_EMAIL}")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "apikey": SUPABASE_KEY,
            },
            json={
                "email": PLATFORM_EMAIL,
                "password": PLATFORM_PASSWORD,
                "email_confirm": True,
                "user_metadata": {"is_platform_owner": True},
            },
        )
        if r.status_code in (200, 201):
            user_data = r.json()
            print(f"  [OK] Supabase Auth platform owner created")
            print(f"       ID: {user_data.get('id')}")
            print(f"       Email: {PLATFORM_EMAIL}")
        else:
            print(f"  [WARN] Supabase create failed: {r.status_code} {r.text[:200]}")

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"  Platform Owner Email:    {PLATFORM_EMAIL}")
    print(f"  Platform Owner Password: {PLATFORM_PASSWORD}")
    print(f"  Login URL:               POST /api/auth/login")
    print(f"  (no Host header required)")
    print(f"\n  IMPORTANT: Change password after first login via Supabase Dashboard")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
