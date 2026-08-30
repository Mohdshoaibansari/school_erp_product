"""Employee module — focused integration smoke test.

Runs against the cloud Supabase (DATABASE_URL from .env).
Does NOT reset the schema — uses existing seeded data.
"""

import os, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

env_path = Path(__file__).parent.parent / ".env"
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key, val)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from kernel.app_factory import create_app
from kernel.middleware import mint_test_jwt
from business.tenant_institution.manifest import manifest as c01_manifest
from kernel.user.manifest import manifest as c02_manifest
from kernel.auth.manifest import manifest as c03_manifest
from kernel.authz.manifest import manifest as c04_manifest
from kernel.config.manifest import manifest as c08_manifest
from kernel.academic.manifest import manifest as c05_manifest
from business.fees.manifest import manifest as fees_manifest
from business.homework.manifest import manifest as homework_manifest
from business.employee.manifest import manifest as employee_manifest

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Get test data
with Session() as s:
    client_id = str(s.execute(text("SELECT id FROM client LIMIT 1")).scalar())
    inst_id = str(s.execute(text("SELECT id FROM institution LIMIT 1")).scalar())
    admin_user = str(s.execute(text("SELECT id FROM app_user WHERE email = 'admin@test-school.com'")).scalar())
    teacher_person_id = str(s.execute(text("SELECT person_id FROM app_user WHERE email = 'teacher@test-school.com'")).scalar())
    emp = s.execute(text("SELECT id, employee_no FROM employee LIMIT 1")).fetchone()

print(f"client_id: {client_id}")
print(f"inst_id: {inst_id}")
print(f"admin_user: {admin_user}")
print(f"teacher_person_id: {teacher_person_id}")
print(f"employee: {emp}")

# Create app
app = create_app([
    c01_manifest, c02_manifest, c03_manifest, c04_manifest,
    c08_manifest, c05_manifest, fees_manifest, homework_manifest,
    employee_manifest,
])

# Mint admin JWT
admin_token = mint_test_jwt(
    user_id=admin_user,
    client_id=client_id,
    institution_id=inst_id,
    roles=["Admin"],
)

def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Host": "test.localhost"}

client = TestClient(app, headers=auth_headers(admin_token))

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name}")
        failed += 1

# ── Test 1: List employees ──
print("\n--- List employees ---")
r = client.get("/api/v1/employees")
check("GET /employees returns 200", r.status_code == 200)
data = r.json()
check("Response has items", "items" in data)
check("Response has total", "total" in data)
check("At least 1 employee", data.get("total", 0) >= 1)
if data.get("items"):
    check("Employee has employee_no", "employee_no" in data["items"][0])
    check("Employee has employment_status", "employment_status" in data["items"][0])

# ── Test 2: Get single employee ──
if emp:
    print("\n--- Get employee ---")
    r = client.get(f"/api/v1/employees/{emp[0]}")
    check("GET /employees/{id} returns 200", r.status_code == 200)
    data = r.json()
    check("Employee has correct id", data.get("id") == str(emp[0]))
    check("Employee has employment_type", data.get("employment_type") is not None)

# ── Test 3: Create employee ──
print("\n--- Create employee ---")
with Session() as s:
    new_pid = uuid.uuid4()
    s.execute(text("""
        INSERT INTO person (id, client_id, name, contact_email, status)
        VALUES (:pid, :cid, 'Test New Employee', 'newemp@test.com', 'Active')
    """), {"pid": new_pid, "cid": client_id})
    s.commit()
    new_person_id = str(new_pid)

r = client.post("/api/v1/employees", json={
    "person_id": new_person_id,
    "employment_type": "FULL_TIME",
    "department": "Science",
    "designation": "Teacher",
    "joining_date": "2026-01-15",
})
check("POST /employees returns 201", r.status_code == 201)
data = r.json()
check("New employee has employee_no", data.get("employee_no") is not None)
check("New employee status is Hired", data.get("employment_status") == "Hired")
check("New employee department is Science", data.get("department") == "Science")
new_emp_id = data.get("id")
print(f"  Created employee: {data.get('employee_no')} (id={new_emp_id})")

# ── Test 4: Activate employee ──
if new_emp_id:
    print("\n--- Activate employee ---")
    r = client.post(f"/api/v1/employees/{new_emp_id}/activate")
    check("POST /activate returns 200", r.status_code == 200)
    check("Status is Active", r.json().get("employment_status") == "Active")

    # ── Test 5: Suspend employee ──
    print("\n--- Suspend employee ---")
    r = client.post(f"/api/v1/employees/{new_emp_id}/suspend")
    check("POST /suspend returns 200", r.status_code == 200)
    check("Status is Suspended", r.json().get("employment_status") == "Suspended")

    # ── Test 6: Re-activate ──
    print("\n--- Re-activate from Suspended ---")
    r = client.post(f"/api/v1/employees/{new_emp_id}/activate")
    check("POST /activate from Suspended returns 200", r.status_code == 200)
    check("Status is Active", r.json().get("employment_status") == "Active")

    # ── Test 7: Deactivate (on-leave) ──
    print("\n--- Deactivate (on-leave) ---")
    r = client.post(f"/api/v1/employees/{new_emp_id}/deactivate")
    check("POST /deactivate returns 200", r.status_code == 200)
    check("Status is On-Leave", r.json().get("employment_status") == "On-Leave")

    # ── Test 8: Re-activate from On-Leave ──
    print("\n--- Re-activate from On-Leave ---")
    r = client.post(f"/api/v1/employees/{new_emp_id}/activate")
    check("POST /activate from On-Leave returns 200", r.status_code == 200)

    # ── Test 9: Terminate ──
    print("\n--- Terminate (resigned) ---")
    r = client.post(f"/api/v1/employees/{new_emp_id}/terminate", json={"terminal_status": "resigned"})
    check("POST /terminate returns 200", r.status_code == 200)
    check("Status is Resigned", r.json().get("employment_status") == "Resigned")

    # ── Test 10: Cannot activate terminal ──
    print("\n--- Cannot activate terminal ---")
    r = client.post(f"/api/v1/employees/{new_emp_id}/activate")
    check("POST /activate on Resigned returns 400", r.status_code == 400)

# ── Test 11: Invalid department ──
print("\n--- Invalid department rejected ---")
r = client.post("/api/v1/employees", json={
    "person_id": str(uuid.uuid4()),
    "employment_type": "FULL_TIME",
    "department": "Astrophysics",
})
check("Invalid department returns 400", r.status_code == 400)

# ── Test 12: Invalid employment_type ──
print("\n--- Invalid employment_type rejected ---")
r = client.post("/api/v1/employees", json={
    "person_id": str(uuid.uuid4()),
    "employment_type": "FREELANCE",
})
check("Invalid employment_type returns 422", r.status_code == 422)

# ── Test 13: Invalid terminal_status ──
if new_emp_id:
    print("\n--- Invalid terminal_status rejected ---")
    r = client.post(f"/api/v1/employees/{new_emp_id}/terminate", json={"terminal_status": "fired"})
    check("Invalid terminal_status returns 422", r.status_code == 422)

# ── Test 14: Update employee ──
if emp:
    print("\n--- Update employee ---")
    r = client.patch(f"/api/v1/employees/{emp[0]}", json={
        "department": "Accounts",
        "designation": "Accountant",
    })
    check("PATCH /employees/{id} returns 200", r.status_code == 200)
    check("Department updated", r.json().get("department") == "Accounts")
    check("Designation updated", r.json().get("designation") == "Accountant")

# ── Summary ──
print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
print(f"{'='*40}")
