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
export HOST="school-e.localhost"  # Slug of the new client we're creating
```

---

## Flow 1: Platform Owner — View All Clients

> **Changes (D1-D36):** Platform owner exists only in Supabase Auth (no `app_user` row).
> Login returns a custom HS256 JWT with `is_platform_owner: true` claim.
> No Host header required for platform endpoints.

### 1.1 Login as Platform Owner

```bash
# NOTE: No Host header! Platform owner is tenant-independent.
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school-erp.com","password":"Shoby@123"}' | python -m json.tool
```

**Expected:** `200 OK` with `{"access_token": "...", "is_platform_owner": true}`

**Save the token:**
```bash
export PLATFORM_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNDk3OTExYy1iZmM1LTQ5ZGItYTI0NC1iY2FmOTJjMzkxNDEiLCJpc19wbGF0Zm9ybV9vd25lciI6dHJ1ZSwiaWF0IjoxNzg0OTU0MjE3LCJleHAiOjE3ODQ5NTc4MTd9.mMoyjQJMqSmcEEFe1BKjQS4l3dazBh8leQLojkzi1eY"
```

### 1.2 List All Clients

```bash
# No Host header needed for platform endpoints
curl -X GET "$BASE_URL/api/v1/platform/clients" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" | python -m json.tool
```

**Expected:** `200 OK` with array of clients

### 1.3 Create a New Client (School E)

First, get the `legal_entity_type_id` via Supabase REST API
(because platform owner can't access lookups):

```bash
curl -X GET "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/legal_entity_type?select=id,name" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" | python -m json.tool
```

**Save the ID:**
```bash
export LEGAL_ENTITY_TYPE_ID="e53252b5-e968-46c7-80a5-545ef35b5b71"
```

Now create the client:

```bash
curl -X POST "$BASE_URL/api/v1/platform/clients" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "School E Academy",
    "legal_name": "School E Academy Pvt Ltd",
    "slug": "school-e",
    "primary_contact_email": "admin@school-e.com",
    "legal_entity_type_id": "'"$LEGAL_ENTITY_TYPE_ID"'"
  }'


**Expected:** `201 Created` with `current_lifecycle_status: "prospective"`

**Save the new client ID:**
bash
export CLIENT_E_ID="c036e9d0-3726-49c4-a46b-65df71d38a25"


### 1.4 Transition Client from Prospective → Active

New clients start as `"prospective"`. They need to be activated before they appear in lists:

bash
curl -X POST "$BASE_URL/api/v1/platform/clients/$CLIENT_E_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "active",
    "reason": "Approved for onboarding"
  }'


**Expected:** `200 OK` with `current_lifecycle_status: "active"`

### 1.5 Client Lifecycle States

| State | Meaning | Transitions |
|---|---|---|
| `prospective` | Newly created | → `active` |
| `active` | Fully operational | → `suspended`, `archived` |
| `suspended` | Temporarily disabled | → `active`, `archived` |
| `archived` | Permanently closed (terminal) | — |

bash
# Suspend
curl -X POST "$BASE_URL/api/v1/platform/clients/$CLIENT_E_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_state": "suspended", "reason": "Payment overdue"}'

# Reactivate
curl -X POST "$BASE_URL/api/v1/platform/clients/$CLIENT_E_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_state": "active", "reason": "Payment received"}'

# Archive (terminal)
curl -X POST "$BASE_URL/api/v1/platform/clients/$CLIENT_E_ID/transition" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_state": "archived", "reason": "Business closed"}'


### 1.6 List All Clients (Should Show Active + Prospective)

bash
curl -X GET "$BASE_URL/api/v1/platform/clients" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" | python -m json.tool


**Expected:** Both `test-school` and `school-e` clients

## Flow 2: Bootstrap School E — Create Admin User

> Platform owner only manages clients. To create institutions and users for School E,
> we bootstrap an admin user via Supabase Admin API + SQL, then login as that admin.

### 2.1 Get Prerequisite IDs via Supabase REST API

```bash
# Get legal_entity_type_id (for clients)
curl -X GET "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/legal_entity_type?select=id,name" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" | python -m json.tool

# Get institution_type (uses name_id FK)
curl -X GET "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/institution_type?select=id,name_id,institution_type_name:name_id(id,name)" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" | python -m json.tool

# Get role IDs (Admin role)
curl -X GET "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/role?select=id,name" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" | python -m json.tool

# Get user_category_id (Academic Staff)
curl -X GET "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/user_category?select=id,name" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" | python -m json.tool
```

**Save the IDs (from your API responses above):**
```bash
# Legal entity type: "Company" → a3b63601-71b4-4863-9ce5-8915d116ec60
export LEGAL_ENTITY_TYPE_ID="a3b63601-71b4-4863-9ce5-8915d116ec60"

# Institution type: check the response from the fixed query above
export INST_TYPE_ID="8159019c-7f56-44f7-a2cf-e323403cee21"

# Admin role → 70343690-695e-46a0-992c-c6eed7fb0c57
export ADMIN_ROLE_ID="70343690-695e-46a0-992c-c6eed7fb0c57"

# Academic Staff category → 20a3b37b-56be-4573-a7ee-b2c5b016fc24
export ACADEMIC_STAFF_ID="20a3b37b-56be-4573-a7ee-b2c5b016fc24"
```

### 2.2 Create Admin User in Supabase Auth + app_user

```bash
# Generate a UUID for the new user
ADMIN_USER_ID=$(uv run python -c "import uuid; print(uuid.uuid4())")
export ADMIN_USER_ID

# Step 1: Create in Supabase Auth
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/auth/v1/admin/users" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$ADMIN_USER_ID\",
    \"email\": \"admin@school-e.com\",
    \"password\": \"Admin@123\",
    \"email_confirm\": true
  }" | python -m json.tool

# Step 2: Insert into app_user (via Supabase REST API)
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/app_user" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=minimal" \
  -d "{
    \"id\": \"$ADMIN_USER_ID\",
    \"client_id\": \"$CLIENT_E_ID\",
    \"institution_id\": \"$INST_E_ID\",
    \"email\": \"admin@school-e.com\",
    \"name\": \"School E Admin\",
    \"user_category_id\": \"$ACADEMIC_STAFF_ID\",
    \"lifecycle_status\": \"active\"
  }"

# Step 3: Assign Admin role
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/role_assignment" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=minimal" \
  -d "{
    \"id\": \"$(uuidgen | tr '[:upper:]' '[:lower:]')\",
    \"user_id\": \"$ADMIN_USER_ID\",
    \"role_id\": \"$ADMIN_ROLE_ID\",
    \"scope_type\": \"institution\",
    \"scope_id\": \"$INST_E_ID\"
  }"
```

### 2.3 Login as School E Admin

```bash
curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Host: school-e.localhost" \
  -d '{"email":"admin@school-e.com","password":"Admin@123"}' | python -m json.tool
```

**Save the token:**
```bash
export ADMIN_E_TOKEN="<paste access_token>"
```

### 2.4 Create Institution Under School E

```bash
curl -X POST "$BASE_URL/api/v1/institutions" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "School E Main Campus",
    "institution_type_id": "'"$INST_TYPE_ID"'"
  }' | python -m json.tool
```

**Save the institution ID:**
```bash
export INST_E_ID="<paste institution id>"
```

### 2.5 Institution Lifecycle Transitions

```bash
# Go live (onboarding → active)
curl -X POST "$BASE_URL/api/v1/institutions/$INST_E_ID/transition" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"active","reason":"Setup complete"}'

# List institutions (should see only School E)
curl -X GET "$BASE_URL/api/v1/institutions" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" | python -m json.tool
```

---

## Flow 3: Create Users Under School E

### 3.1 Get Prerequisite IDs (using admin token)

```bash
# Get user categories
curl -X GET "$BASE_URL/api/v1/lookups/user-categories" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" | python -m json.tool

# Get roles
curl -X GET "$BASE_URL/api/v1/lookups/roles" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" | python -m json.tool
```

### 3.2 Create Users

```bash
# Create teacher
curl -X POST "$BASE_URL/api/v1/users" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"teacher@school-e.com",
    "name":"School E Teacher",
    "user_category_id":"<Academic Staff id>",
    "institution_id":"'"$INST_E_ID"'"
  }' | python -m json.tool

# Create student
curl -X POST "$BASE_URL/api/v1/users" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"student@school-e.com",
    "name":"School E Student",
    "user_category_id":"<Learner id>",
    "institution_id":"'"$INST_E_ID"'"
  }' | python -m json.tool
```

### 3.3 Activate Users (Set Password + Lifecycle)

```bash
# Get user ID from app_user
curl -X GET "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/app_user?email=eq.teacher@school-e.com&select=id" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" | python -m json.tool

export TEACHER_ID="<paste id>"

# Set password in Supabase Auth
curl -X PUT "https://ripscmqvzkipsqtmfdry.supabase.co/auth/v1/admin/users/$TEACHER_ID" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"password":"Teacher@123","email_confirm":true}'

# Activate in app_user
curl -X PATCH "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/app_user?id=eq.$TEACHER_ID" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=minimal" \
  -d '{"lifecycle_status":"active"}'
```

### 3.4 List Users (Tenant Isolation)

```bash
# School E admin sees only School E users
curl -X GET "$BASE_URL/api/v1/users" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" | python -m json.tool
```

---

## Flow 4: Test Tenant Isolation

### 4.1 Login as School E Admin

```bash
curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Host: school-e.localhost" \
  -d '{
    "email": "admin@school-e.com",
    "password": "Admin@123"
  }' | python -m json.tool
```


**Save the token:**
bash
export ADMIN_E_TOKEN="<paste access_token here>"


### 4.2 School E Admin Lists Institutions (Should See Only School E)

bash
curl -X GET "$BASE_URL/api/v1/institutions" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" | python -m json.tool

**Expected:** Only School E's institutions

### 4.3 School E Admin Tries to Access School A's Data (Should Fail)

bash
# Try to access test-school context with School E token
curl -X GET "$BASE_URL/api/v1/institutions" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: test-school.localhost" | python -m json.tool

**Expected:** `401 Unauthorized` or `403 Forbidden` — cross-tenant access blocked

**Why it fails:** The middleware validates the JWT and resolves the user. The user's `client_id` (School E) doesn't match the Host header's client (School A). Cross-tenant check fails.

---

## Flow 5: Create Fee Type at School E (Isolation Test)

### 5.1 School E Admin Creates Fee Type

bash
curl -X POST "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "School E Tuition",
    "description": "Annual tuition for School E",
    "default_amount": 8000.00,
    "institution_id": "'"$INST_E_ID"'"
  }'


**Expected:** `201 Created`

### 5.2 Platform Owner Lists Fee Types at School A (Should NOT See School E's)

bash
curl -X GET "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: test-school.localhost" | python -m json.tool

**Expected:** Only School A's fee types (not School E's "School E Tuition")

### 5.3 Platform Owner Lists Fee Types at School E (Should See School E's)

bash
curl -X GET "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" | python -m json.tool

**Expected:** Only School E's fee types

---

## Flow 6: Test Lifecycle State Transitions

### 6.1 Suspend a User

bash
curl -X POST "$BASE_URL/api/v1/users/$ADMIN_E_USER_ID/transition" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "suspended",
    "reason": "Testing suspension"
  }'


**Expected:** `200 OK` with user lifecycle_status = "suspended"

### 6.2 Suspended User Tries to Login (Should Fail)

bash
curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Host: school-e.localhost" \
  -d '{
    "email": "admin@school-e.com",
    "password": "<password>"
  }'


**Expected:** `403 Forbidden` — "Account is not active. Status: suspended."

### 6.3 Reactivate User

bash
curl -X POST "$BASE_URL/api/v1/users/$ADMIN_E_USER_ID/transition" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: school-e.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "new_state": "active",
    "reason": "Reactivated for testing"
  }'


---

## Flow 7: Test Permission Enforcement (C-04 Authorization)

### 7.1 Create Teacher User at School A

bash
curl -X POST "$BASE_URL/api/v1/users" \
  -H "Authorization: Bearer $ADMIN_E_TOKEN" \
  -H "Host: test-school.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@test-school.com",
    "name": "Test Teacher",
    "user_category_id": "<Academic Staff category id>",
    "institution_id": "<School A institution id>"
  }'


### 7.2 Activate Teacher (direct DB update for testing)

bash
PGPASSWORD="Infosys!657627sh" psql "postgresql://postgres@db.ripscmqvzkipsqtmfdry.supabase.co:5432/postgres" -c "
  UPDATE app_user SET lifecycle_status = 'active' WHERE email = 'teacher@test-school.com';
"


### 7.3 Login as Teacher

bash
curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Host: test-school.localhost" \
  -d '{
    "email": "teacher@test-school.com",
    "password": "<password>"
  }'


**Save the token:**
bash
export TEACHER_TOKEN="<paste access_token here>"


### 7.4 Teacher Tries to Create Fee Type (Should Fail — No Permission)

bash
curl -X POST "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Host: test-school.localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Unauthorized Fee",
    "default_amount": 100.00,
    "institution_id": "<institution_id>"
  }'


**Expected:** `403 Forbidden` — "Permission denied" (Teacher role doesn't have `fee.create`)

### 7.5 Teacher Lists Fee Types (Should Work — Has `fee.read`)

bash
curl -X GET "$BASE_URL/api/v1/fee-types" \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Host: test-school.localhost" | python -m json.tool

**Expected:** `200 OK` with list of fee types

---

## Flow 8: Test Homework Isolation

### 8.1 Teacher Creates Homework

bash
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


**Expected:** `201 Created`

### 8.2 Student at School A Lists Homework

bash
curl -X GET "$BASE_URL/api/v1/homeworks" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Host: test-school.localhost" | python -m json.tool

**Expected:** Sees homeworks for their grade_level + section

### 8.3 Student at School E Lists Homework (Should NOT See School A's)

bash
curl -X GET "$BASE_URL/api/v1/homeworks" \
  -H "Authorization: Bearer $STUDENT_B_TOKEN" \
  -H "Host: school-e.localhost" | python -m json.tool

**Expected:** Empty or only School E's homeworks — School A's homework NOT visible

---

## Summary of Multi-Tenancy Checks

| Test | Expected Result |
|---|---|
| Platform owner sees all clients | ✅ |
| School A admin sees only School A institutions | ✅ |
| School E admin sees only School E institutions | ✅ |
| School E token at School A host → blocked | ✅ 401/403 |
| School A fee types NOT visible at School E | ✅ Isolated |
| Suspended user can't log in | ✅ 403 |
| Teacher can't create fee types | ✅ 403 |
| Teacher can list fee types | ✅ 200 |
| School A homework NOT visible at School E | ✅ Isolated |

---

## Quick Reference: User Credentials

| Role | Email | Password | Host Header |
|---|---|---|---|
| Platform Owner | `platform@test-school.com` | `Platform@123` | `test-school.localhost` |
| Admin (School A) | `admin@test-school.com` | `Admin@123` | `test-school.localhost` |
| Teacher (School A) | `teacher@test-school.com` | `Teacher@123` | `test-school.localhost` |
| Student (School A) | `student@test-school.com` | `Student@123` | `test-school.localhost` |

**Note:** For School E users, you need to create them first (Flow 3) and set their password via Supabase Auth or direct DB update.

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
