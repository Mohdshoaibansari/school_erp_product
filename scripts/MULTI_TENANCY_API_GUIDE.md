# Multi-Tenancy API Testing Guide

> **Purpose:** Test multi-tenancy using curl/Postman — no frontend needed.  
> **Focus:** Client isolation, institution scoping, user-per-institution, cross-tenant blocking.

---

## Prerequisites

1. Backend running: `cd backend && uv run uvicorn main:app --host 127.0.0.1 --port 8000`
2. Migrations applied: `uv run alembic upgrade head`
3. Seed data: `uv run python -m scripts.seed_data`

---

## Environment Variables (for convenience)

```bash
# Set these in your terminal for easier copy-paste
export BASE_URL="http://127.0.0.1:8000"
export HOST="test-school.localhost"  # Resolves to client slug "test-school"
```

---

## Flow 1: Platform Owner — View All Clients

### 1.1 Login as Platform Owner

```bash
curl -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -H "Host: $HOST" \
  -d '{
    "email": "platform@test-school.com",
    "password": "Platform@123"
  }'
```

**Expected:** `200 OK` with `{ "access_token": "...", "refresh_token": "...", ... }`

**Save the token:**
```bash
export PLATFORM_TOKEN="eyJhbGciOiJFUzI1NiIsImtpZCI6IjQyZjhkOWQxLWMwZGEtNDliNi04ODBlLTE4MjhkZTFlMDA2NyIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3JpcHNjbXF2emtpcHNxdG1mZHJ5LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI2ZDVjMGU3OC1mNDRmLTQxNDUtODczMS01MGQyOTM5YWM4ZGIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzg0Njk1MDc2LCJpYXQiOjE3ODQ2OTE0NzYsImVtYWlsIjoicGxhdGZvcm1AdGVzdC1zY2hvb2wuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbF92ZXJpZmllZCI6dHJ1ZX0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3ODQ2OTE0NzZ9XSwic2Vzc2lvbl9pZCI6ImNmOTc2NDFhLTk5ZGItNGJiMi1hN2Q2LTY2MjM2ZTE4MTVjNSIsImlzX2Fub255bW91cyI6ZmFsc2V9.F3QvyYRBpKaEs0LrAXLBAuB2R0_vGHepeZYEYCIVM0MmejPonghnu_VqItk9Zg90sL-39CYX4IJ5W7QIYTLVGA"
```

### 1.2 List All Clients

```bash
curl -X GET "$BASE_URL/api/v1/platform/clients" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: $HOST"
```

**Expected:** `200 OK` with array of clients (should include `test-school`)

### 1.3 Create a New Client (School D)

```bash
curl -X POST "$BASE_URL/api/v1/platform/clients" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "School D Academy",
    "legal_name": "School D Academy Pvt Ltd",
    "slug": "school-d",
    "primary_contact_email": "admin@school-d.com",
    "legal_entity_type_id": "81e77718-098b-45a0-a1ee-931441804ff8"
  }'
```

**Expected:** `201 Created` with `current_lifecycle_status: "prospective"`

**Save the new client ID:**
```bash
export CLIENT_D_ID="465fda3e-241b-45ac-95c2-9264e760e33b"
```

### 1.4 Transition Client from Prospective → Active

New clients start as `"prospective"`. They need to be activated before they appear in lists:

```bash
curl -X POST "$BASE_URL/api/v1/platform/clients/$CLIENT_D_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "active",
    "reason": "Approved for onboarding"
  }'
```

**Expected:** `200 OK` with `current_lifecycle_status: "active"`

### 1.5 Client Lifecycle States

| State | Meaning | Transitions |
|---|---|---|
| `prospective` | Newly created | → `active` |
| `active` | Fully operational | → `suspended`, `archived` |
| `suspended` | Temporarily disabled | → `active`, `archived` |
| `archived` | Permanently closed (terminal) | — |

```bash
# Suspend
curl -X POST "$BASE_URL/api/v1/platform/clients/$CLIENT_D_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{"new_state": "suspended", "reason": "Payment overdue"}'

# Reactivate
curl -X POST "$BASE_URL/api/v1/platform/clients/$CLIENT_D_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{"new_state": "active", "reason": "Payment received"}'

# Archive (terminal)
curl -X POST "$BASE_URL/api/v1/platform/clients/$CLIENT_D_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{"new_state": "archived", "reason": "Business closed"}'
```

### 1.6 List All Clients (Should Show Active + Prospective)

```bash
curl -X GET "$BASE_URL/api/v1/platform/clients" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: $HOST"
```

**Expected:** Both `test-school` and `school-d` clients

## Flow 2: Create Institutions Under Different Clients

### 2.1 Get Institution Types (needed for creating institutions)

```bash
curl -X GET "$BASE_URL/api/v1/platform/institution-types" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: $HOST"
```

**Expected:** Array of institution types. Copy the `id` of "School" type.

### 2.2 Create Institution Under School D

```bash
curl -X POST "$BASE_URL/api/v1/institutions" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "School D Main Campus",
    "institution_type_id": "8159019c-7f56-44f7-a2cf-e323403cee21"
  }'
```

**Expected:** `201 Created` with `current_lifecycle_status: "onboarding"`

**Save the institution ID:**
```bash
export INST_D_ID="1afd34dd-3b73-48de-9026-edb0320f1df1"
```

### 2.3 Institution Lifecycle States

| State | Meaning | Transitions |
|---|---|---|
| `onboarding` | Newly created, setting up | → `active`, `archived` |
| `active` | Fully operational | → `inactive`, `archived` |
| `inactive` | Temporarily disabled | → `active`, `archived` |
| `archived` | Permanently closed | → `active` (can be reactivated) |

```
onboarding → active → inactive → archived
    ↑           ↑         |
    └───────────┘─────────┘
```

### 2.4 Go Live (onboarding → active)

Institutions start as `"onboarding"`. They need to be activated:

```bash
curl -X POST "$BASE_URL/api/v1/institutions/$INST_D_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "active",
    "reason": "Setup complete, ready for operations"
  }'
```

**Expected:** `200 OK` with `current_lifecycle_status: "active"`

### 2.5 Deactivate Institution (active → inactive)

```bash
curl -X POST "$BASE_URL/api/v1/institutions/$INST_D_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "inactive",
    "reason": "Compliance issue"
  }'
```

### 2.6 Reactivate Institution (inactive → active)

```bash
curl -X POST "$BASE_URL/api/v1/institutions/$INST_D_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "active",
    "reason": "Compliance resolved"
  }'
```

### 2.7 Archive Institution (active/inactive → archived)

```bash
curl -X POST "$BASE_URL/api/v1/institutions/$INST_D_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "archived",
    "reason": "School closed"
  }'
```

**Note:** Archived institutions CAN be reactivated (archived → active). This is different from Client lifecycle where archived is terminal.

### 2.8 List Institutions

```bash
curl -X GET "$BASE_URL/api/v1/institutions" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost"
```

**Expected:** Only School D's institutions (tenant isolation)

---

## Flow 3: Create Users at Different Institutions

### 3.1 Create Admin User at School D

```bash
curl -X POST "$BASE_URL/api/v1/users" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@school-d.com",
    "name": "School D Admin",
    "user_category_id": "<paste Academic Staff category id>",
    "institution_id": "'"$INST_B_ID"'"
  }'
```

**Note:** Get `user_category_id` first:

```bash
curl -X GET "$BASE_URL/api/v1/lookups/user-categories" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: $HOST"
```

**Save the user ID:**
```bash
export ADMIN_B_USER_ID="<paste user id here>"
```

### 3.2 Assign Admin Role to School D User

```bash
# Get role IDs first
curl -X GET "$BASE_URL/api/v1/lookups/roles" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: $HOST"

# Assign Admin role
curl -X POST "$BASE_URL/api/v1/users/$ADMIN_B_USER_ID/roles" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "role_id": "<paste Admin role id>"
  }'
```

### 3.3 Activate the User (Set Password)

The user was created with `lifecycle_status=invited`. They need to activate via invite token.

**Option A: Direct DB update (for testing only)**

```bash
PGPASSWORD="Infosys!657627sh" psql "postgresql://postgres@db.ripscmqvzkipsqtmfdry.supabase.co:5432/postgres" -c "
  UPDATE app_user SET lifecycle_status = 'active' WHERE email = 'admin@school-d.com';
"
```

**Option B: Create Supabase Auth user + activate via API (proper flow)**

First, create the Supabase Auth user (the seed script does this, but for new users you need to do it manually or via the admin create flow).

For testing purposes, Option A (direct DB update) is simpler.

---

## Flow 4: Test Tenant Isolation

### 4.1 Login as School D Admin

```bash
curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Host: school-d.localhost" \
  -d '{
    "email": "admin@school-d.com",
    "password": "<password set during activation>"
  }'
```

**Save the token:**
```bash
export ADMIN_B_TOKEN="<paste access_token here>"
```

### 4.2 School D Admin Lists Institutions (Should See Only School D)

```bash
curl -X GET "$BASE_URL/api/v1/institutions" \
  -H "Authorization: Bearer $ADMIN_B_TOKEN" \
  -H "Host: school-d.localhost"
```

**Expected:** Only School D's institutions

### 4.3 School D Admin Tries to Access School A's Data (Should Fail)

```bash
# Try to access test-school context with School D token
curl -X GET "$BASE_URL/api/v1/institutions" \
  -H "Authorization: Bearer $ADMIN_B_TOKEN" \
  -H "Host: test-school.localhost"
```

**Expected:** `401 Unauthorized` or `403 Forbidden` — cross-tenant access blocked

**Why it fails:** The middleware validates the JWT and resolves the user. The user's `client_id` (School D) doesn't match the Host header's client (School A). Cross-tenant check fails.

---

## Flow 5: Create Fee Type at School D (Isolation Test)

### 5.1 School D Admin Creates Fee Type

```bash
curl -X POST "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $ADMIN_B_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "School D Tuition",
    "description": "Annual tuition for School D",
    "default_amount": 8000.00,
    "institution_id": "'"$INST_B_ID"'"
  }'
```

**Expected:** `201 Created`

### 5.2 Platform Owner Lists Fee Types at School A (Should NOT See School D's)

```bash
curl -X GET "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: test-school.localhost"
```

**Expected:** Only School A's fee types (not School D's "School D Tuition")

### 5.3 Platform Owner Lists Fee Types at School D (Should See School D's)

```bash
curl -X GET "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost"
```

**Expected:** Only School D's fee types

---

## Flow 6: Test Lifecycle State Transitions

### 6.1 Suspend a User

```bash
curl -X POST "$BASE_URL/api/v1/users/$ADMIN_B_USER_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "suspended",
    "reason": "Testing suspension"
  }'
```

**Expected:** `200 OK` with user lifecycle_status = "suspended"

### 6.2 Suspended User Tries to Login (Should Fail)

```bash
curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Host: school-d.localhost" \
  -d '{
    "email": "admin@school-d.com",
    "password": "<password>"
  }'
```

**Expected:** `403 Forbidden` — "Account is not active. Status: suspended."

### 6.3 Reactivate User

```bash
curl -X POST "$BASE_URL/api/v1/users/$ADMIN_B_USER_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: school-d.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "active",
    "reason": "Reactivated for testing"
  }'
```

---

## Flow 7: Test Permission Enforcement (C-04 Authorization)

### 7.1 Create Teacher User at School A

```bash
curl -X POST "$BASE_URL/api/v1/users" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Host: test-school.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@test-school.com",
    "name": "Test Teacher",
    "user_category_id": "<Academic Staff category id>",
    "institution_id": "<School A institution id>"
  }'
```

### 7.2 Activate Teacher (direct DB update for testing)

```bash
PGPASSWORD="Infosys!657627sh" psql "postgresql://postgres@db.ripscmqvzkipsqtmfdry.supabase.co:5432/postgres" -c "
  UPDATE app_user SET lifecycle_status = 'active' WHERE email = 'teacher@test-school.com';
"
```

### 7.3 Login as Teacher

```bash
curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Host: test-school.localhost" \
  -d '{
    "email": "teacher@test-school.com",
    "password": "<password>"
  }'
```

**Save the token:**
```bash
export TEACHER_TOKEN="<paste access_token here>"
```

### 7.4 Teacher Tries to Create Fee Type (Should Fail — No Permission)

```bash
curl -X POST "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Host: test-school.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Unauthorized Fee",
    "default_amount": 100.00,
    "institution_id": "<institution_id>"
  }'
```

**Expected:** `403 Forbidden` — "Permission denied" (Teacher role doesn't have `fee.create`)

### 7.5 Teacher Lists Fee Types (Should Work — Has `fee.read`)

```bash
curl -X GET "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Host: test-school.localhost"
```

**Expected:** `200 OK` with list of fee types

---

## Flow 8: Test Homework Isolation

### 8.1 Teacher Creates Homework

```bash
curl -X POST "$BASE_URL/api/v1/homeworks" \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Host: test-school.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Math Homework Ch 5",
    "description": "Complete exercises 1-10",
    "subject": "Mathematics",
    "grade_level": "Grade 5",
    "section": "A",
    "due_date": "2026-08-15",
    "max_score": 100
  }'
```

**Expected:** `201 Created`

### 8.2 Student at School A Lists Homework

```bash
curl -X GET "$BASE_URL/api/v1/homeworks" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Host: test-school.localhost"
```

**Expected:** Sees homeworks for their grade_level + section

### 8.3 Student at School D Lists Homework (Should NOT See School A's)

```bash
curl -X GET "$BASE_URL/api/v1/homeworks" \
  -H "Authorization: Bearer $STUDENT_B_TOKEN" \
  -H "Host: school-d.localhost"
```

**Expected:** Empty or only School D's homeworks — School A's homework NOT visible

---

## Summary of Multi-Tenancy Checks

| Test | Expected Result |
|---|---|
| Platform owner sees all clients | ✅ |
| School A admin sees only School A institutions | ✅ |
| School D admin sees only School D institutions | ✅ |
| School D token at School A host → blocked | ✅ 401/403 |
| School A fee types NOT visible at School D | ✅ Isolated |
| Suspended user can't log in | ✅ 403 |
| Teacher can't create fee types | ✅ 403 |
| Teacher can list fee types | ✅ 200 |
| School A homework NOT visible at School D | ✅ Isolated |

---

## Quick Reference: User Credentials

| Role | Email | Password | Host Header |
|---|---|---|---|
| Platform Owner | `platform@test-school.com` | `Platform@123` | `test-school.localhost` |
| Admin (School A) | `admin@test-school.com` | `Admin@123` | `test-school.localhost` |
| Teacher (School A) | `teacher@test-school.com` | `Teacher@123` | `test-school.localhost` |
| Student (School A) | `student@test-school.com` | `Student@123` | `test-school.localhost` |

**Note:** For School D users, you need to create them first (Flow 3) and set their password via Supabase Auth or direct DB update.

---

## Troubleshooting

**401 "Invalid or expired JWT":**
- Token expired (1 hour default). Re-login.
- Wrong Host header — must match the client slug.

**403 "Permission denied — no roles assigned":**
- User has no role_assignment in the database.
- Check: `SELECT * FROM role_assignment WHERE user_id = '<user_id>';`

**403 "Account is not active":**
- User lifecycle_status is not 'active'.
- Check: `SELECT lifecycle_status FROM app_user WHERE email = '<email>';`

**404 "Not Found":**
- Wrong URL path. Check the route prefix (`/api/v1/` for business, `/api/auth/` for auth).
