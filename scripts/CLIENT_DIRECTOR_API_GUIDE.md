# Client Director API Guide

> **Role:** Manages a single client (tenant). Creates institutions, users, and
> manages day-to-day operations. Cannot create or manage other clients.
> **Host header required:** `Host: <slug>.localhost` (resolves client context).
> **Prerequisite:** Client must be created by Platform Owner first.

---

## Environment

```bash
export BASE_URL="http://127.0.0.1:8000"

export HOST="meerutpublic.localhost"
```

---

## 1. Login

```bash
curl -X POST $BASE_URL/api/auth/login -H "Content-Type: application/json" -H "Host: $HOST" -d '{"email":"shoby.ansari586@gmail.com","password":"Admin@123"}' | python -m json.tool
```

**Save token:**
```bash
export TOKEN="<paste access_token from response>"
```

---

## 2. Lookup Tables (Reference Data)

```bash
# User categories
curl -X GET $BASE_URL/api/v1/lookups/user-categories -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" | python -m json.tool

# Roles
curl -X GET $BASE_URL/api/v1/lookups/roles -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" | python -m json.tool

# Institution types (available for all authenticated users)
curl -X GET $BASE_URL/api/v1/lookups/institution-types -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" | python -m json.tool
```

> **Institution types** are managed by the platform owner, but any
> authenticated user can list them for institution creation.

---

## 3. Institutions

> **The platform owner defines what institution types are available** (School, College,
> etc.). You pick from those types when creating your institutions.
> Run `GET /api/v1/platform/institution-types` as platform owner first to see available types.

### 3.1 Create Institution

```bash
curl -X POST $BASE_URL/api/v1/institutions -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" -H "Content-Type: application/json" -d '{"display_name":"Meerut Public School","institution_type_id":"8159019c-7f56-44f7-a2cf-e323403cee21","legal_name":"Meerut Public School Society","code":"MPS","primary_contact_email":"info@meerutpublicschool.com","primary_contact_phone":"+91-121-2400000","established_year":1995,"affiliation_number":"CBSE/2130456","affiliation_board":"CBSE"}' | python -m json.tool
```

**Save institution ID:**
```bash
export INST_ID="76754ce1-7c2d-451f-848d-7f1b746f8a86"
```

### 3.2 Activate Institution

```bash
curl -X POST $BASE_URL/api/v1/institutions/$INST_ID/transition -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" -H "Content-Type: application/json" -d '{"new_state":"active","reason":"Setup complete"}' | python -m json.tool
```

### 3.3 Institution Lifecycle

| State | Meaning | Transitions |
|---|---|---|
| `onboarding` | New, being set up | → `active`, `archived` |
| `active` | Fully operational | → `inactive`, `archived` |
| `inactive` | Temporarily disabled | → `active`, `archived` |
| `archived` | Closed (reactivatable) | → `active` |

```bash
# Deactivate
curl -X POST $BASE_URL/api/v1/institutions/$INST_ID/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"inactive","reason":"Term break"}'

# Reactivate
curl -X POST $BASE_URL/api/v1/institutions/$INST_ID/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"active","reason":"Term resumed"}'

# Archive
curl -X POST $BASE_URL/api/v1/institutions/$INST_ID/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"archived","reason":"Permanent closure"}'
```

### 3.4 List Institutions

```bash
curl -X GET $BASE_URL/api/v1/institutions -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" | python -m json.tool
```

### 3.5 Remove an Institution

> No hard delete — archive it instead.

```bash
# List first to get the institution ID
curl -X GET $BASE_URL/api/v1/institutions -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" | python -m json.tool

# Archive it
curl -X POST $BASE_URL/api/v1/institutions/<institution_id>/transition -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" -H "Content-Type: application/json" -d '{"new_state":"archived","reason":"No longer needed"}'
```

---

## 4. Users

### 4.1 Create User

```bash
curl -X POST $BASE_URL/api/v1/users -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" -H "Content-Type: application/json" -d '{"email":"teacher@meerutpublic.com","name":"Rahul Sharma","user_category_id":"20a3b37b-56be-4573-a7ee-b2c5b016fc24","institution_id":"'$INST_ID'"}' | python -m json.tool
```

**Save user ID:**
```bash
export TEACHER_ID="<paste id from response>"
```

### 4.1.2 Create Institute Admin

```bash
curl -X POST $BASE_URL/api/v1/users -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" -H "Content-Type: application/json" -d '{"email":"admin@meerutpublic.com","name":"Vikram Singh","user_category_id":"20a3b37b-56be-4573-a7ee-b2c5b016fc24","institution_id":"'$INST_ID'"}' | python -m json.tool
```

**Save admin ID:**
```bash
export ADMIN_ID="15a5c462-fc79-4038-aa30-d3165498e645"
```

Assign Admin role (institution-scoped):
```bash
curl -X POST $BASE_URL/api/v1/users/$ADMIN_ID/roles -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" -H "Content-Type: application/json" -d '{"role_id":"70343690-695e-46a0-992c-c6eed7fb0c57"}'
```

> **Note:** New users are created with `lifecycle_status: invited`. They need
> password + activation before they can login (see sections 4.4 and 4.5).

### 4.2 List Users

```bash
# All users in this client
curl -X GET $BASE_URL/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" | python -m json.tool

# Filter by institution
curl -X GET "$BASE_URL/api/v1/users?institution_id=$INST_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" | python -m json.tool

# Filter by lifecycle
curl -X GET "$BASE_URL/api/v1/users?lifecycle_status=active" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" | python -m json.tool
```

### 4.3 Assign Teacher Role

> The institute admin role was already assigned in 4.1.2. Now assign role to teacher.

```bash
curl -X POST $BASE_URL/api/v1/users/$TEACHER_ID/roles -H "Authorization: Bearer $TOKEN" -H "Host: $HOST" -H "Content-Type: application/json" -d '{"role_id":"5d1efdc6-b15d-403f-8dac-bbacbcb5ff3c"}'
```

### 4.4 Activate Institute Admin (Set Password + Lifecycle)

```bash
# Set password in Supabase Auth
curl -X PUT "https://ripscmqvzkipsqtmfdry.supabase.co/auth/v1/admin/users/$ADMIN_ID" --http1.1 \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"password":"Admin@123","email_confirm":true}'

# Activate lifecycle
curl -X PATCH "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/app_user?id=eq.$ADMIN_ID" --http1.1 \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"lifecycle_status":"active"}'
```

Admin login:
```bash
curl -X POST $BASE_URL/api/auth/login -H "Content-Type: application/json" -H "Host: $HOST" -d '{"email":"admin@meerutpublic.com","password":"Admin@123"}' | python -m json.tool
```

### 4.5 Activate Teacher (Set Password + Lifecycle)

```bash
# Set password in Supabase Auth
curl -X PUT "https://ripscmqvzkipsqtmfdry.supabase.co/auth/v1/admin/users/$TEACHER_ID" --http1.1 \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"password":"Teacher@123","email_confirm":true}'

# Activate lifecycle
curl -X PATCH "https://ripscmqvzkipsqtmfdry.supabase.co/rest/v1/app_user?id=eq.$TEACHER_ID" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"lifecycle_status":"active"}'
```

### 4.6 User Lifecycle

| State | Meaning |
|---|---|
| `invited` | Created, not yet activated |
| `active` | Can login and use system |
| `suspended` | Temporarily blocked |
| `archived` | Permanently deactivated (terminal) |

```bash
# Suspend user
curl -X POST $BASE_URL/api/v1/users/$TEACHER_ID/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"suspended","reason":"Policy violation"}'

# Reactivate
curl -X POST $BASE_URL/api/v1/users/$TEACHER_ID/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{"new_state":"active","reason":"Issue resolved"}'
```

### 4.7 Delete User

```bash
curl -X DELETE $BASE_URL/api/v1/users/$TEACHER_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST"
```

---

## 5. Fees Management

### 5.1 Fee Types

```bash
# Create fee type (institution-scoped)
curl -X POST $BASE_URL/api/v1/fee-types \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Tuition Fee",
    "amount":5000.00,
    "institution_id":"'$INST_ID'",
    "academic_term":"2026-27"
  }' | python -m json.tool

# List fee types
curl -X GET $BASE_URL/api/v1/fee-types \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" | python -m json.tool
```

### 5.2 Assign Fee to Student

```bash
curl -X POST $BASE_URL/api/v1/fee-assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{
    "fee_type_id":"<fee type id>",
    "user_id":"<student id>",
    "due_date":"2026-08-01"
  }' | python -m json.tool
```

### 5.3 Record Payment

```bash
curl -X POST $BASE_URL/api/v1/payments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{
    "fee_assignment_id":"<assignment id>",
    "amount":5000.00,
    "payment_method":"Online Transfer"
  }' | python -m json.tool
```

---

## 6. Homework Management

### 6.1 Create Homework

```bash
curl -X POST $BASE_URL/api/v1/homeworks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Math Worksheet",
    "description":"Complete pages 10-15",
    "institution_id":"'$INST_ID'",
    "assigned_by":"<teacher user id>",
    "due_date":"2026-07-30"
  }' | python -m json.tool
```

### 6.2 Submit Homework (Student)

```bash
curl -X POST $BASE_URL/api/v1/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{
    "homework_id":"<homework id>",
    "student_id":"<student id>",
    "content":"Completed all problems"
  }' | python -m json.tool
```

### 6.3 Grade Submission

```bash
curl -X POST $BASE_URL/api/v1/grades \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d '{
    "submission_id":"<submission id>",
    "score":85,
    "feedback":"Good work!"
  }' | python -m json.tool
```

---

## 7. Tenant Isolation Verification

```bash
# Try accessing another client's data (should return empty or 403)
curl -X GET $BASE_URL/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: test-school.localhost" | python -m json.tool

# Expected: empty list or 403 (cross-tenant blocked)
```

---

## Reference IDs

| Entity | ID |
|---|---|
| User Category: Academic Staff | `20a3b37b-56be-4573-a7ee-b2c5b016fc24` |
| User Category: Learner | `024ffc86-e4d4-4901-9449-fd6546843909` |
| Role: Admin | `70343690-695e-46a0-992c-c6eed7fb0c57` |
| Role: Teacher | `5d1efdc6-b15d-403f-8dac-bbacbcb5ff3c` |
| Role: Student | `03bd67b4-8c4e-4e3b-861e-e7548ba930e8` |
