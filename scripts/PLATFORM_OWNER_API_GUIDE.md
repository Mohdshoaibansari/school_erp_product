# Platform Owner API Guide

> **Role:** Super-admin managing all clients (tenants). No institution access.
> **Setup:** Platform owner exists only in Supabase Auth (`user_metadata.is_platform_owner: true`).
> **No Host header required** — platform owner is client-independent.

---

## Environment

```bash
export BASE_URL="http://127.0.0.1:8000"
```

---

## 1. Login

```bash
curl -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school-erp.com","password":"Shoby@123"}' | python -m json.tool
```

**Expected:** `200 OK` with `is_platform_owner: true`

**Save token:**
```bash
export PLATFORM_TOKEN="<paste access_token>"
```

---

## 2. List All Clients

```bash
curl -X GET $BASE_URL/api/v1/platform/clients \
  -H "Authorization: Bearer $PLATFORM_TOKEN" | python -m json.tool
```

---

## 3. Create a New Client

```bash
curl -X POST $BASE_URL/api/v1/platform/clients \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "My School Academy",
    "legal_name": "My School Academy Pvt Ltd",
    "slug": "my-school",
    "primary_contact_email": "admin@myschool.com",
    "legal_entity_type_id": "a3b63601-71b4-4863-9ce5-8915d116ec60"
  }' | python -m json.tool
```

**Save the client ID:**
```bash
export CLIENT_ID="<paste id from response>"
```

---

## 4. Activate Client

New clients start as `prospective`. Activate them:

```bash
curl -X POST $BASE_URL/api/v1/platform/clients/$CLIENT_ID/transition \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"active","reason":"Onboarding approved"}' | python -m json.tool
```

---

## 5. Client Lifecycle States

| State | Meaning | From → To |
|---|---|---|
| `prospective` | New, not yet live | → `active`, `archived` |
| `active` | Fully operational | → `suspended`, `archived` |
| `suspended` | Temporarily disabled | → `active`, `archived` |
| `archived` | Closed (terminal) | — |

```bash
# Suspend
curl -X POST $BASE_URL/api/v1/platform/clients/$CLIENT_ID/transition \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"suspended","reason":"Payment overdue"}'

# Reactivate
curl -X POST $BASE_URL/api/v1/platform/clients/$CLIENT_ID/transition \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"active","reason":"Payment resolved"}'

# Archive (terminal)
curl -X POST $BASE_URL/api/v1/platform/clients/$CLIENT_ID/transition \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"archived","reason":"Business closed"}'
```

---

## 6. Get Client Details

```bash
curl -X GET $BASE_URL/api/v1/platform/clients/$CLIENT_ID \
  -H "Authorization: Bearer $PLATFORM_TOKEN" | python -m json.tool
```

---

## 7. Bootstrap Client Director (First User)

> Create the first user for the new client. This user will manage everything
> else — institutions, users, fees, etc.

```bash
# Set service role key (for Supabase Admin API)
export SUPABASE_SERVICE_ROLE_KEY="<from .env>"

# Generate a UUID for the new user
DIRECTOR_ID=$(uv run python -c "import uuid; print(uuid.uuid4())")

# Step 1: Create in Supabase Auth
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/auth/v1/admin/users" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"$DIRECTOR_ID\",\"email\":\"admin@myschool.com\",\"password\":\"Admin@123\",\"email_confirm\":true}"

# Step 2: Insert into app_user (no institution — client-level user)
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/app_user" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"$DIRECTOR_ID\",\"client_id\":\"$CLIENT_ID\",\"email\":\"admin@myschool.com\",\"name\":\"Client Director\",\"user_category_id\":\"20a3b37b-56be-4573-a7ee-b2c5b016fc24\",\"lifecycle_status\":\"active\"}"

# Step 3: Assign Admin role (client-scoped)
ROLE_ID=$(uv run python -c "import uuid; print(uuid.uuid4())")
curl -X POST "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/role_assignment" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"$ROLE_ID\",\"user_id\":\"$DIRECTOR_ID\",\"role_id\":\"70343690-695e-46a0-992c-c6eed7fb0c57\",\"scope_type\":\"client\",\"scope_id\":\"$CLIENT_ID\"}"

echo "Client Director created! Email: admin@myschool.com | Password: Admin@123"
```

---

## 8. Manage Institution Types

```bash
# List
curl -X GET $BASE_URL/api/v1/platform/institution-types \
  -H "Authorization: Bearer $PLATFORM_TOKEN" | python -m json.tool

# Create
curl -X POST $BASE_URL/api/v1/platform/institution-types \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"College","code":"COLLEGE"}' | python -m json.tool
```

---

## 9. Ownership Transfers

```bash
# Request transfer
curl -X POST $BASE_URL/api/v1/platform/ownership-transfers \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "institution_id":"<institution id>",
    "to_client_id":"<target client id>",
    "reason":"Reorganization"
  }' | python -m json.tool

# Approve transfer
curl -X POST "$BASE_URL/api/v1/platform/ownership-transfers/<approval_id>/approve?to_client_id=<target>" \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"consent_source":true,"consent_dest":true,"reason":"Approved"}'
```

---

## Reference IDs

| Entity | ID |
|---|---|
| Legal Entity: Company | `a3b63601-71b4-4863-9ce5-8915d116ec60` |
| User Category: Academic Staff | `20a3b37b-56be-4573-a7ee-b2c5b016fc24` |
| Role: Admin | `70343690-695e-46a0-992c-c6eed7fb0c57` |
