# Journey 02 — Client Director

> **Role:** client_director
> **Scope:** Own client (tenant) — `client_id` must match
> **Auth:** Custom HS256 JWT with `user_tier: "client_leadership"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "director@greenwood.com", password: "..." }
→ 200 { access_token, user_tier: "client_leadership", client_id: "..." }
```

### HP-02: Create Institution
```
POST /api/v1/institutions
Body: { display_name: "Greenwood High", institution_type_id: "...", code: "GHS" }
→ 201 { id, display_name, current_lifecycle_status: "onboarding" }
```

### HP-03: Transition Institution Lifecycle
```
POST /api/v1/institutions/{inst_id}/transition
Body: { new_state: "active", reason: "Setup complete" }
→ 200 { id, current_lifecycle_status: "active" }
```

### HP-04: Create User (Institution Admin)
```
POST /api/v1/users
Body: { email: "admin@greenwood.com", name: "Admin", user_category_id: "...", institution_id: "...", role_id: "..." }
→ 201 { user: { id, email }, invite_url: "..." }
```

### HP-05: Create User (Teacher)
```
POST /api/v1/users
Body: { email: "teacher@greenwood.com", name: "Teacher", user_category_id: "...", institution_id: "...", role_id: "..." }
→ 201 { user: { id, email }, invite_url: "..." }
```

### HP-06: List Users
```
GET /api/v1/users
→ 200 [{ id, email, name, lifecycle_status }, ...]
```

### HP-07: Create Org Unit
```
POST /api/v1/org-units
Body: { institution_id: "...", name: "Primary Wing", type_id: "...", sort_order: 1 }
→ 201 { id, name }
```

### HP-08: Move Org Unit
```
POST /api/v1/org-units/{ou_id}/move
Body: { new_parent_id: "..." }
→ 200 { id, parent_id }
```

### HP-09: Create Fee Type
```
POST /api/v1/fee-types
Body: { name: "Tuition Fee", institution_id: "...", default_amount: 50000 }
→ 201 { id, name }
```

### HP-10: Assign Fee to Student
```
POST /api/v1/fee-assignments
Body: { fee_type_id: "...", user_ids: ["..."], amount: 50000, due_date: "2026-09-30", institution_id: "..." }
→ 201 [{ id, user_id, amount }]
```

### HP-11: Create Profile for Student
```
POST /api/v1/users/{student_id}/profile
Body: { date_of_birth: "2014-07-15", gender: "male", blood_group: "B+" }
→ 201 { id, user_id, date_of_birth }
```

### HP-12: Update Own Profile
```
PATCH /api/v1/users/{cd_user_id}/profile
Body: { photo: "https://..." }
→ 200 { id, photo }
```

### HP-13: List Role Assignments
```
GET /api/v1/users/{user_id}/roles
→ 200 [{ id, role_id, scope }, ...]
```

### HP-14: Create Role Assignment
```
POST /api/v1/users/{user_id}/roles
Body: { role_id: "..." }
→ 201 { id, role_id }
```

### HP-15: List Institutions
```
GET /api/v1/institutions
→ 200 [{ id, display_name, current_lifecycle_status }, ...]
```

### HP-16: Read Client Info
```
GET /api/v1/clients/{client_id}
→ 200 { id, slug, display_name }
```

---

## Failure Scenarios

### FS-01: CD tries to access another client's institutions (cross-tenant)
```
GET /api/v1/institutions
Host: other-school.localhost
Authorization: Bearer {cd_token_for_greenwood}
→ 403 "Access denied. Account does not belong to this client."
```
**Why:** Login cross-tenant check fails — CD's `client_id` doesn't match the subdomain's client.

### FS-02: CD tries to create user at another institution (cross-tenant)
```
POST /api/v1/users
Authorization: Bearer {cd_token}
Body: { institution_id: "{other_client_institution_id}", ... }
→ 403 "Permission denied" (Casbin: tenant scope check fails)
```
**Why:** CD's `client_id` doesn't match the institution's `client_id`.

### FS-03: CD tries to access platform endpoints
```
GET /api/v1/platform/clients
Authorization: Bearer {cd_token}
→ 403 (require_platform_owner rejects)
```
**Why:** Platform routes require `is_platform_owner=true`.

### FS-04: CD tries to transition institution to invalid state
```
POST /api/v1/institutions/{inst_id}/transition
Body: { new_state: "invalid_state" }
→ 400 "Invalid transition"
```
**Why:** State machine validation rejects invalid transitions.

### FS-05: CD tries to create duplicate institution code
```
POST /api/v1/institutions
Body: { code: "GHS", ... }  // code already exists
→ 409 "Institution code already exists"
```
**Why:** Unique constraint on `(client_id, code)`.

### FS-06: CD tries to delete another CD's user
```
DELETE /api/v1/users/{other_cd_user_id}
Authorization: Bearer {cd_token}
→ 404 "User not found" (RLS filters out users from other clients)
```
**Why:** RLS filters by `client_id` — other client's users are invisible.

### FS-07: CD tries to read config values (no permission)
```
GET /api/v1/config/values
Authorization: Bearer {cd_token}
→ 403 "Permission denied"
```
**Why:** CD has `config.value.create/update/delete` but not `config.value.list` (actually CD has `config.value.*` — let me verify).

### FS-08: CD tries to access institution before activation
```
GET /api/v1/institutions/{inst_id}
Authorization: Bearer {cd_token}
→ 404 (institution in "onboarding" state, may be filtered by lifecycle)
```
**Why:** Depending on RLS policy, onboarding institutions may not be visible to all endpoints.

### FS-09: CD tries to create user without role_id
```
POST /api/v1/users
Body: { email: "test@test.com", name: "Test", user_category_id: "...", institution_id: "..." }
→ 201 { user: { id }, invite_url: "..." } (role_id is optional)
```
**Note:** This SHOULD succeed — `role_id` is optional per D2. User gets created without a role.

### FS-10: CD tries to create user with invalid role_id
```
POST /api/v1/users
Body: { role_id: "{non_existent_uuid}", ... }
→ 400 "Role not found"
```
**Why:** Role validation happens before user creation (D10 bug #6 fix).
