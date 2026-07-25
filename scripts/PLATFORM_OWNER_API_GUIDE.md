# Platform Owner API Guide

> **Role:** Super-admin managing all clients (tenants). No institution access.
> **Setup:** Platform owner exists only in Supabase Auth (`user_metadata.is_platform_owner: true`).
> **No Host header required** — platform owner is client-independent.
> **Next steps for client users:** See `scripts/CLIENT_DIRECTOR_API_GUIDE.md`

---

## Environment

```bash
export BASE_URL="http://127.0.0.1:8000"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpcHNjbXF2emtpcHNxdG1mZHJ5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzIzODI0MywiZXhwIjoyMDk4ODE0MjQzfQ.ugz-v6WHEX-oKonbjlw5QJmPe-3BFLw3w4UnlMKAC5U"
```

---

## 1. Login

```bash
curl -X POST $BASE_URL/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@school-erp.com","password":"Shoby@123"}' | python -m json.tool
```

**Expected:** `200 OK` with `is_platform_owner: true`

**Save token:**
```bash
export PLATFORM_TOKEN="<paste access_token>"
```

---

## 2. List All Clients

```bash
curl -X GET $BASE_URL/api/v1/platform/clients -H "Authorization: Bearer $PLATFORM_TOKEN" | python -m json.tool
```

---

## 3. Create & Activate a New Client

### 3.1 Create Client

```bash
curl -X POST $BASE_URL/api/v1/platform/clients -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"display_name":"My School Academy","legal_name":"My School Academy Pvt Ltd","slug":"my-school","primary_contact_email":"admin@myschool.com","legal_entity_type_id":"a3b63601-71b4-4863-9ce5-8915d116ec60"}' | python -m json.tool
```

**Save the client ID:**
```bash
export CLIENT_ID="<paste id from response>"
```

### 3.2 Activate Client

```bash
curl -X POST $BASE_URL/api/v1/platform/clients/$CLIENT_ID/transition -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"new_state":"active","reason":"Onboarding approved"}' | python -m json.tool
```

---

## 4. Bootstrap Client Director

> Creates the first user for the new client. This user manages everything
> else — institutions, users, fees, homework, etc.

### 4.1 Create in Supabase Auth

```bash
export DIRECTOR_ID=$(uv run python -c "import uuid; print(uuid.uuid4())")
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/auth/v1/admin/users" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Content-Type: application/json" -d "{\"id\":\"$DIRECTOR_ID\",\"email\":\"admin@myschool.com\",\"password\":\"Admin@123\",\"email_confirm\":true}"
```

> **Important:** The `$DIRECTOR_ID` from the response must match what you use in step 4.2. If the response shows a different UUID, override:
> ```bash
> export DIRECTOR_ID="<id from response>"
> ```

### 4.2 Insert into app_user

> `institution_id` is NULL — Client Director manages the whole client, not a single institution.

```bash
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/app_user" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" -H "Content-Type: application/json" -d "{\"id\":\"$DIRECTOR_ID\",\"client_id\":\"$CLIENT_ID\",\"email\":\"admin@myschool.com\",\"name\":\"Client Director\",\"user_category_id\":\"20a3b37b-56be-4573-a7ee-b2c5b016fc24\",\"lifecycle_status\":\"active\"}"
```

### 4.3 Assign Admin Role

> The `role_assignment` row needs its own UUID primary key (`id`). This is NOT the role reference — the role reference is the hardcoded `role_id`.

```bash
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/role_assignment" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" -H "Content-Type: application/json" -d "{\"id\":\"$(uv run python -c 'import uuid; print(uuid.uuid4())')\",\"client_id\":\"$CLIENT_ID\",\"user_id\":\"$DIRECTOR_ID\",\"role_id\":\"0b542f1d-4fa3-4771-8526-af7febba2aa0\",\"scope\":\"client\"}"
```

### 4.4 Verify — Login as Client Director

```bash
curl -X POST $BASE_URL/api/auth/login -H "Content-Type: application/json" -H "Host: my-school.localhost" -d '{"email":"admin@myschool.com","password":"Admin@123"}' | python -m json.tool
```

> **Next:** Save the token and follow `CLIENT_DIRECTOR_API_GUIDE.md` for institution/user management.

---

## 5. Client Lifecycle Management

| State | Meaning | Transitions |
|---|---|---|
| `prospective` | New, not yet live | → `active`, `archived` |
| `active` | Fully operational | → `suspended`, `archived` |
| `suspended` | Temporarily disabled | → `active`, `archived` |
| `archived` | Closed (terminal) | — |

```bash
# Suspend
curl -X POST $BASE_URL/api/v1/platform/clients/$CLIENT_ID/transition -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"new_state":"suspended","reason":"Payment overdue"}'

# Reactivate
curl -X POST $BASE_URL/api/v1/platform/clients/$CLIENT_ID/transition -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"new_state":"active","reason":"Payment resolved"}'

# Archive (terminal)
curl -X POST $BASE_URL/api/v1/platform/clients/$CLIENT_ID/transition -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"new_state":"archived","reason":"Business closed"}'
```

---

## 6. Manage Institution Types

> **Platform owner defines what kinds of institutions can exist** (School, College,
> Coaching Center, etc.). The Client Director picks from these types when creating
> their own institutions.

```bash
# List existing types (already seeded)
curl -X GET $BASE_URL/api/v1/platform/institution-types -H "Authorization: Bearer $PLATFORM_TOKEN" | python -m json.tool
```

> Creating new types requires a `name_id` FK to `institution_type_name` table.
> Use Supabase REST API to add new types if needed:
> ```bash
> NAME_ID=$(uv run python -c "import uuid; print(uuid.uuid4())")
> curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/institution_type_name" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" -H "Content-Type: application/json" -d "{\"id\":\"$NAME_ID\",\"name\":\"College\"}"
> curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/institution_type" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" -H "Content-Type: application/json" -d "{\"id\":\"$(uv run python -c 'import uuid; print(uuid.uuid4())')\",\"name_id\":\"$NAME_ID\",\"code\":\"COLLEGE\"}"
> ```

---

## 7. Ownership Transfers

```bash
# Request
curl -X POST $BASE_URL/api/v1/platform/ownership-transfers -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"institution_id":"<id>","to_client_id":"<target>","reason":"Reorganization"}' | python -m json.tool

# Approve (use approval_id from request response)
curl -X POST "$BASE_URL/api/v1/platform/ownership-transfers/<approval_id>/approve?to_client_id=<target>" -H "Authorization: Bearer $PLATFORM_TOKEN" -H "Content-Type: application/json" -d '{"consent_source":true,"consent_dest":true,"reason":"Approved"}'
```

---

## Reference IDs

| Entity | ID |
|---|---|
| Legal Entity: Company | `a3b63601-71b4-4863-9ce5-8915d116ec60` |
| Legal Entity: Pvt Ltd | `81e77718-098b-45a0-a1ee-931441804ff8` |
| User Category: Academic Staff | `20a3b37b-56be-4573-a7ee-b2c5b016fc24` |
| User Category: Learner | `024ffc86-e4d4-4901-9449-fd6546843909` |
| Role: Admin | `0b542f1d-4fa3-4771-8526-af7febba2aa0` |
| Role: Teacher | `5d1efdc6-b15d-403f-8dac-bbacbcb5ff3c` |
| Role: Student | `03bd67b4-8c4e-4e3b-861e-e7548ba930e8` |
