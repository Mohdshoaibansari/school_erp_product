"""Bootstrap script — seeds test data on cloud Supabase.

Run: cd backend && uv run python -m scripts.seed_data
"""

import os, uuid, asyncio
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key, val)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import httpx

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine, expire_on_commit=False)

async def create_supabase_user(email: str, password: str, user_metadata: dict | None = None) -> str | None:
    """Create (or reuse) a Supabase Auth user; returns the actual user id string."""
    headers = {"Authorization": f"Bearer {SUPABASE_KEY}", "apikey": SUPABASE_KEY}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=headers,
            json={"email": email, "password": password, "email_confirm": True,
                  "user_metadata": user_metadata or {}},
        )
        if r.status_code in (200, 201):
            print(f"  [OK] Supabase user created: {email}")
            return r.json().get("id")
        if r.status_code == 422 and "email_exists" in r.text:
            # Reuse the existing user's id (list + match by email), then fix metadata/password
            r2 = await client.get(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=headers,
                params={"page": 1, "per_page": 200},
            )
            users = r2.json().get("users", []) if r2.status_code == 200 else []
            for u in users:
                if u.get("email") == email:
                    uid = u.get("id")
                    await client.put(
                        f"{SUPABASE_URL}/auth/v1/admin/users/{uid}",
                        headers=headers,
                        json={"user_metadata": user_metadata or {}, "password": password},
                    )
                    print(f"  [OK] Supabase user exists, reused + updated: {email}")
                    return uid
        print(f"  [WARN] Supabase create user {email}: {r.status_code} {r.text[:120]}")
        return None

async def main():
    print("SEED: Seeding cloud Supabase...\n")

    # ============================================================
    # 1. Create Client
    # ============================================================
    client_id = uuid.uuid4()
    inst_id = uuid.uuid4()

    with Session() as s:
        # Insert legal_entity_type if needed
        s.execute(text("INSERT INTO legal_entity_type (id, name) VALUES (gen_random_uuid(), 'Company') ON CONFLICT DO NOTHING"))
        s.flush()
        let_id = s.execute(text("SELECT id FROM legal_entity_type LIMIT 1")).fetchone()[0]

        # Client — reuse existing (by slug) or create (idempotent re-runs)
        existing_client = s.execute(text("SELECT id FROM client WHERE slug = 'test-school' LIMIT 1")).fetchone()
        if existing_client:
            client_id = existing_client[0]
        else:
            s.execute(text("""
                INSERT INTO client (id, display_name, legal_name, slug, legal_entity_type_id, primary_contact_email, current_lifecycle_status)
                VALUES (:cid, 'Test School', 'Test School Legal', 'test-school', :let_id, 'admin@test-school.com', 'active')
            """), {"cid": client_id, "let_id": let_id})
            s.flush()

        # Insert institution_type_name + institution_type
        s.execute(text("INSERT INTO institution_type_name (id, name) VALUES (gen_random_uuid(), 'School') ON CONFLICT DO NOTHING"))
        s.flush()
        itn_id = s.execute(text("SELECT id FROM institution_type_name LIMIT 1")).fetchone()[0]
        itype_id = uuid.uuid4()
        s.execute(text("INSERT INTO institution_type (id, name_id, code, is_system) VALUES (:id, :nid, 'INTG_SCH', true) ON CONFLICT DO NOTHING"), {"id": itype_id, "nid": itn_id})
        s.flush()
        itype_id = s.execute(text("SELECT id FROM institution_type LIMIT 1")).fetchone()[0]

        # Institution — reuse existing (by client + name) or create
        existing_inst = s.execute(text("SELECT id FROM institution WHERE client_id = :cid AND display_name = 'Test Institution' LIMIT 1"), {"cid": client_id}).fetchone()
        if existing_inst:
            inst_id = existing_inst[0]
        else:
            s.execute(text("""
                INSERT INTO institution (id, client_id, institution_type_id, display_name, current_lifecycle_status)
                VALUES (:iid, :cid, :itype, 'Test Institution', 'active')
            """), {"iid": inst_id, "cid": client_id, "itype": itype_id})
        s.commit()
    print(f"[OK] Client + Institution ready (client_id={client_id})")

    # ============================================================
    # 2. Create users in Supabase Auth + app_user table
    # ============================================================
    roles = {
        "admin": ("admin@test-school.com", "Admin@123", "Admin"),
        "teacher": ("teacher@test-school.com", "Teacher@123", "Teacher"),
        "student": ("student@test-school.com", "Student@123", "Student"),
        "platform_owner": ("platform@test-school.com", "Platform@123", "platform_owner"),
    }

    user_ids = {}
    with Session() as s:
        role_ids = {r[0]: r[1] for r in s.execute(text("SELECT name, id FROM role")).fetchall()}
        admin_role = role_ids.get("Admin", list(role_ids.values())[0])
        teacher_role = role_ids.get("Teacher", list(role_ids.values())[0])
        student_role = role_ids.get("Student", list(role_ids.values())[0])
        po_role = role_ids.get("platform_owner", list(role_ids.values())[0])

        for role_key, (email, password, role_name) in roles.items():
            user_metadata = {"is_platform_owner": True} if role_name == "platform_owner" else {"user_tier": "institution"}
            uid_str = await create_supabase_user(email, password, user_metadata)
            if not uid_str:
                print(f"  [WARN] skipping {email} (no Supabase id)")
                continue
            uid = uuid.UUID(uid_str)
            user_ids[role_key] = uid

            # Reconcile: remove a stale app_user row with a different id for this email
            existing = s.execute(text("SELECT id FROM app_user WHERE email = :email LIMIT 1"), {"email": email}).fetchone()
            if existing and existing[0] != uid:
                s.execute(text("DELETE FROM role_assignment WHERE user_id = :uid"), {"uid": existing[0]})
                s.execute(text("DELETE FROM app_user WHERE id = :uid"), {"uid": existing[0]})
                s.execute(text("DELETE FROM user_account WHERE id = :uid"), {"uid": existing[0]})
                existing = None

            if existing and existing[0] == uid:
                continue  # already present and matching

            # Insert person row (independent UUID, D3a)
            person_id = uuid.uuid4()
            s.execute(text("""
                INSERT INTO person (id, client_id, name, contact_email, status)
                VALUES (:pid, :cid, :name, :email, 'active')
            """), {"pid": person_id, "cid": client_id, "name": f"Test {role_name}", "email": email})

            # Insert parent user_account row (required by app_user.id FK)
            s.execute(text("INSERT INTO user_account (id) VALUES (:id) ON CONFLICT (id) DO NOTHING"), {"id": uid})

            # Insert app_user (no name, no user_category_id — person_id links to person)
            s.execute(text("""
                INSERT INTO app_user (id, client_id, institution_id, email, person_id, lifecycle_status)
                VALUES (:id, :cid, :iid, :email, :pid, 'active')
            """), {"id": uid, "cid": client_id, "iid": inst_id, "email": email, "pid": person_id})

            # Assign role
            role_map = {"Admin": admin_role, "Teacher": teacher_role, "Student": student_role, "platform_owner": po_role}
            is_po = role_name == "platform_owner"
            s.execute(text("""
                INSERT INTO role_assignment (id, client_id, user_id, role_id, scope)
                VALUES (gen_random_uuid(), :cid, :uid, :rid, :scope)
            """), {"cid": client_id, "uid": uid, "rid": role_map[role_name], "scope": "Platform" if is_po else "Test School"})

        s.commit()
    print(f"[OK] Users created: admin, teacher, student (all password: <Role>@123)")

    # ============================================================
    # 3. Create sample fee type + assignment + payment
    # ============================================================
    with Session() as s:
        ft_id = uuid.uuid4()
        s.execute(text("""
            INSERT INTO fee_type (id, client_id, institution_id, name, description, default_amount)
            VALUES (:id, :cid, :iid, 'Tuition Fee', 'Term 1 Tuition', 5000.00)
        """), {"id": ft_id, "cid": client_id, "iid": inst_id})

        fa_id = uuid.uuid4()
        s.execute(text("""
            INSERT INTO fee_assignment (id, client_id, institution_id, user_id, fee_type_id, amount, due_date, status, assigned_by)
            VALUES (:id, :cid, :iid, :uid, :ftid, 5000.00, '2026-12-31', 'pending', :uid)
        """), {"id": fa_id, "cid": client_id, "iid": inst_id, "uid": user_ids["student"], "ftid": ft_id})

        s.execute(text("""
            INSERT INTO payment (id, client_id, institution_id, fee_assignment_id, amount, payment_method, receipt_number, recorded_by)
            VALUES (gen_random_uuid(), :cid, :iid, :faid, 2000.00, 'Cash', 'REC-000001', :uid)
        """), {"cid": client_id, "iid": inst_id, "faid": fa_id, "uid": user_ids["admin"]})

        # Update assignment status to partial
        s.execute(text("UPDATE fee_assignment SET status = 'partial' WHERE id = :id"), {"id": fa_id})
        s.commit()
    print("[OK] Sample fee data created")

    # ============================================================
    # 4. Create sample homework + submission + grade
    # ============================================================
    with Session() as s:
        hw_id = uuid.uuid4()
        s.execute(text("""
            INSERT INTO homework (id, client_id, institution_id, title, description, due_date, max_score, status, assigned_by)
            VALUES (:id, :cid, :iid, 'Math Ch 5 Worksheet', 'Complete problems 1-20', '2026-08-01', 100, 'active', :uid)
        """), {"id": hw_id, "cid": client_id, "iid": inst_id, "uid": user_ids["teacher"]})

        sub_id = uuid.uuid4()
        s.execute(text("""
            INSERT INTO submission (id, client_id, institution_id, homework_id, student_id, content, status, submitted_at)
            VALUES (:id, :cid, :iid, :hwid, :uid, '1. Answer: 42. 2. Answer: 3.14', 'submitted', now())
        """), {"id": sub_id, "cid": client_id, "iid": inst_id, "hwid": hw_id, "uid": user_ids["student"]})

        s.execute(text("""
            INSERT INTO grade (id, client_id, institution_id, submission_id, score, max_score, feedback, graded_by, graded_at)
            VALUES (gen_random_uuid(), :cid, :iid, :sid, 85, 100, 'Good work!', :uid, now())
        """), {"cid": client_id, "iid": inst_id, "sid": sub_id, "uid": user_ids["teacher"]})

        s.execute(text("UPDATE submission SET status = 'graded' WHERE id = :id"), {"id": sub_id})
        s.commit()
    print("[OK] Sample homework data created")

    # ============================================================
    # Summary
    # ============================================================
    print(f"""
╔══════════════════════════════════════════╗
║         SEED: SEED COMPLETE                ║
╠══════════════════════════════════════════╣
║  Client slug:   test-school             ║
║  Institution:   Test Institution        ║
║                                          ║
║  USER: Admin:      admin@test-school.com   ║
║     Password:   Admin@123               ║
║     Role:       Admin (full access)     ║
║                                          ║
║  USER: Teacher:    teacher@test-school.com ║
║     Password:   Teacher@123             ║
║     Role:       Teacher (HW CRUD+grade) ║
║                                          ║
║  USER: Student:    student@test-school.com ║
║     Password:   Student@123             ║
║     Role:       Student (submit+view)   ║
║                                          ║
║  Sample data:                            ║
║    • 1 Fee Type (Tuition)               ║
║    • 1 Fee Assignment (partial paid)    ║
║    • 1 Payment (₹2000)                  ║
║    • 1 Homework (Math)                  ║
║    • 1 Submission (graded 85/100)       ║
╚══════════════════════════════════════════╝
""")

if __name__ == "__main__":
    asyncio.run(main())
