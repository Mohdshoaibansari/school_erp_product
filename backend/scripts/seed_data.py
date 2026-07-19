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

async def create_supabase_user(uid: str, email: str, password: str):
    """Create a user in Supabase Auth via Admin API."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={"Authorization": f"Bearer {SUPABASE_KEY}", "apikey": SUPABASE_KEY},
            json={"id": uid, "email": email, "password": password, "email_confirm": True},
        )
        if r.status_code not in (200, 201):
            print(f"  [WARN] Supabase create user {email}: {r.status_code} {r.text[:100]}")
        else:
            print(f"  [OK] Supabase user created: {email}")

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

        s.execute(text("""
            INSERT INTO client (id, display_name, legal_name, slug, legal_entity_type_id, primary_contact_email, current_lifecycle_status)
            VALUES (:cid, 'Test School', 'Test School Legal', 'test-school', :let_id, 'admin@test-school.com', 'active')
            ON CONFLICT DO NOTHING
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

        s.execute(text("""
            INSERT INTO institution (id, client_id, institution_type_id, display_name, current_lifecycle_status)
            VALUES (:iid, :cid, :itype, 'Test Institution', 'active')
            ON CONFLICT DO NOTHING
        """), {"iid": inst_id, "cid": client_id, "itype": itype_id})
        s.commit()
    print(f"[OK] Client + Institution created (client_id={client_id})")

    # ============================================================
    # 2. Create users in Supabase Auth + app_user table
    # ============================================================
    roles = {
        "admin": ("admin@test-school.com", "Admin@123", "Admin"),
        "teacher": ("teacher@test-school.com", "Teacher@123", "Teacher"),
        "student": ("student@test-school.com", "Student@123", "Student"),
    }

    user_ids = {}
    with Session() as s:
        cat_ids = {r[0]: r[1] for r in s.execute(text("SELECT name, id FROM user_category")).fetchall()}
        role_ids = {r[0]: r[1] for r in s.execute(text("SELECT name, id FROM role")).fetchall()}
        learner_cat = cat_ids.get("Learner", list(cat_ids.values())[0])
        staff_cat = cat_ids.get("Academic Staff", list(cat_ids.values())[0])
        admin_role = role_ids.get("Admin", list(role_ids.values())[0])
        teacher_role = role_ids.get("Teacher", list(role_ids.values())[0])
        student_role = role_ids.get("Student", list(role_ids.values())[0])

        for role_key, (email, password, role_name) in roles.items():
            uid = uuid.uuid4()
            user_ids[role_key] = uid
            cat = learner_cat if role_key == "student" else staff_cat

            # Insert app_user
            s.execute(text("""
                INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status)
                VALUES (:id, :cid, :iid, :email, :name, :cat, 'active')
            """), {"id": uid, "cid": client_id, "iid": inst_id, "email": email, "name": f"Test {role_name}", "cat": cat})

            # Assign role
            s.execute(text("""
                INSERT INTO role_assignment (id, client_id, user_id, role_id, scope)
                VALUES (gen_random_uuid(), :cid, :uid, :rid, 'Test School')
            """), {"cid": client_id, "uid": uid, "rid": {"Admin": admin_role, "Teacher": teacher_role, "Student": student_role}[role_name]})

            # Create Supabase Auth user
            await create_supabase_user(str(uid), email, password)

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
            INSERT INTO fee_assignment (id, client_id, institution_id, user_id, fee_type_id, amount, due_date, academic_term, status, assigned_by)
            VALUES (:id, :cid, :iid, :uid, :ftid, 5000.00, '2026-12-31', '2026 Term 1', 'pending', :uid)
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
            INSERT INTO homework (id, client_id, institution_id, title, description, subject, grade_level, section, due_date, max_score, status, assigned_by)
            VALUES (:id, :cid, :iid, 'Math Ch 5 Worksheet', 'Complete problems 1-20', 'Mathematics', 'Grade 5', 'A', '2026-08-01', 100, 'active', :uid)
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
