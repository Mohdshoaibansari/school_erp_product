"""One-shot greenfield wipe: delete all Supabase Auth users except the Platform Owner.

Run BEFORE migrations 011 + 012 when starting fresh.
Uses Supabase Admin API with the service_role key.
Per D14 of the client-user-bootstrap PRD.

Usage:
    cd backend
    uv run python -m scripts.greenfield_wipe_auth_users

Environment variables (from .env):
    SUPABASE_URL     - e.g. https://ripscmqvzkipsqtmfdry.supabase.co
    SUPABASE_SERVICE_ROLE_KEY - the secret service_role key from Supabase Dashboard

Keeps: admin@school-erp.com (the Platform Owner)
Deletes: all other users
"""

from __future__ import annotations

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [WIPE] %(message)s")
logger = logging.getLogger(__name__)


PLATFORM_OWNER_EMAIL = "admin@school-erp.com"


def wipe():
    supabase_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    import httpx

    client = httpx.Client(base_url=supabase_url, timeout=30)
    headers = {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key,
    }

    # List users from paginated Admin API
    users_to_delete = []
    page = 1
    while True:
        resp = client.get("/auth/v1/admin/users", headers=headers, params={"page": page, "per_page": 50})
        if resp.status_code != 200:
            logger.error("Failed to list users: %s %s", resp.status_code, resp.text)
            sys.exit(1)

        data = resp.json()
        users = data.get("users", [])
        if not users:
            break

        for user in users:
            email = user.get("email", "")
            user_id = user.get("id", "")
            is_po = user.get("user_metadata", {}).get("is_platform_owner", False)
            if email == PLATFORM_OWNER_EMAIL or is_po:
                logger.info("KEEP: %s (%s) — Platform Owner", email, user_id)
            else:
                users_to_delete.append((user_id, email))
                logger.info("DELETE: %s (%s)", email, user_id)
        page += 1

    if not users_to_delete:
        logger.info("No users to delete. Already clean.")
        return

    print(f"\nAbout to delete {len(users_to_delete)} users (keeping PO: {PLATFORM_OWNER_EMAIL})")
    confirm = input("Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        logger.info("Aborted.")
        return

    for user_id, email in users_to_delete:
        resp = client.delete(f"/auth/v1/admin/users/{user_id}", headers=headers)
        if resp.status_code == 200:
            logger.info("✓ Deleted: %s (%s)", email, user_id)
        else:
            logger.warning("✗ Failed to delete: %s (%s) — %s %s", email, user_id, resp.status_code, resp.text)

    logger.info("Wipe complete.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env")
    wipe()
