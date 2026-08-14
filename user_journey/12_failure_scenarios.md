# Journey 12 — Failure Scenarios (Cross-Role, Cross-Tenant, Lifecycle)

> **Scope:** All roles
> **Purpose:** Comprehensive failure scenarios that span multiple roles and resources

---

## 1. Cross-Tenant Failures

### FT-01: CD from Client A tries to login at Client B's subdomain
```
POST /api/auth/login
Host: other-school.localhost
Authorization: Bearer {cd_token_for_greenwood}
→ 403 "Access denied. Account does not belong to this client."
```
**Why:** Login cross-tenant check: `ctx.client_id != user_obj.client_id`

### FT-02: Institution user from School A tries to login at School B's subdomain
```
POST /api/auth/login
Host: other-school.localhost
Body: { email: "teacher@school-a.com", password: "..." }
→ 403 "Access denied. Account does not belong to this client."
```
**Why:** Login cross-tenant check: `ctx.client_id != user_dto.client_id`

### FT-03: CD tries to read institution from another client
```
GET /api/v1/institutions/{other_client_inst_id}
Authorization: Bearer {cd_token}
→ 404 (RLS filters out — institution not visible)
```
**Why:** RLS filters by `client_id`. Other client's institutions are invisible.

### FT-04: CD tries to create user at another client's institution
```
POST /api/v1/users
Authorization: Bearer {cd_token}
Body: { institution_id: "{other_client_inst_id}", ... }
→ 403 "Permission denied" (Casbin: tenant scope check fails)
```
**Why:** CD's `client_id` doesn't match the institution's `client_id`.

---

## 2. Cross-Role Failures

### FR-01: Teacher tries to do Admin-only operations
```
POST /api/v1/fee-types
Authorization: Bearer {teacher_token}
→ 403 "Permission denied"
```
**Why:** Teacher has `fee_assignment.read` but NOT `fee.create`.

### FR-02: Student tries to do Teacher-only operations
```
POST /api/v1/homeworks
Authorization: Bearer {student_token}
→ 403 "Permission denied"
```
**Why:** Student has `homework.read` but NOT `homework.create`.

### FR-03: Parent tries to do any write operation
```
POST /api/v1/homeworks
Authorization: Bearer {parent_token}
→ 403 "Permission denied"
```
**Why:** Parent has only `user.read` — no write permissions at all.

### FR-04: HOD tries to do Admin-only operations
```
POST /api/v1/users
Authorization: Bearer {hod_token}
Body: { email: "test@test.com", ... }
→ 403 "Permission denied"
```
**Why:** HOD has `user.read` but NOT `user.create`.

### FR-05: Institution Admin tries to do CD-only operations
```
POST /api/v1/institutions
Authorization: Bearer {inst_admin_token}
→ 403 "Permission denied"
```
**Why:** Institution Admin has `institution.read/update` but NOT `institution.create`.

---

## 3. Lifecycle Gating Failures

### FL-01: Suspended user tries to login
```
POST /api/auth/login
Body: { email: "suspended@greenwood.com", password: "..." }
→ 403 "Account is not active. Status: suspended."
```
**Why:** Login checks `lifecycle_status == "active"` before proceeding.

### FL-02: Archived user tries to login
```
POST /api/auth/login
Body: { email: "archived@greenwood.com", password: "..." }
→ 403 "Account is not active. Status: archived."
```
**Why:** Archived is terminal — no login allowed.

### FL-03: Invited user tries to login (not yet activated)
```
POST /api/auth/login
Body: { email: "invited@greenwood.com", password: "..." }
→ 401 "Invalid email or password"
```
**Why:** User has no password set in Supabase Auth (D11 — created during activate). Login fails at Supabase level.

### FL-04: CD tries to transition institution from invalid state
```
POST /api/v1/institutions/{inst_id}/transition
Body: { new_state: "active" }  // institution is already "active"
→ 400 "Invalid transition"
```
**Why:** State machine rejects invalid transitions (e.g., active→active).

### FL-05: CD tries to archive institution that has active users
```
POST /api/v1/institutions/{inst_id}/transition
Body: { new_state: "archived" }
→ 400 "Cannot archive institution with active users"
```
**Why:** Business rule — can't archive institution while users are active.

---

## 4. Data Validation Failures

### FD-01: Create user with duplicate email
```
POST /api/v1/users
Body: { email: "existing@greenwood.com", ... }
→ 409 "Email already taken"
```
**Why:** Unique constraint on `app_user.email`.

### FD-02: Create institution with duplicate code
```
POST /api/v1/institutions
Body: { code: "GHS", ... }  // code already exists
→ 409 "Institution code already exists"
```
**Why:** Unique constraint on `(client_id, code)`.

### FD-03: Create user with invalid role_id
```
POST /api/v1/users
Body: { role_id: "{non_existent_uuid}", ... }
→ 400 "Role not found"
```
**Why:** Role validation happens before user creation (D10 bug #6 fix).

### FD-04: Create user with invalid institution_id
```
POST /api/v1/users
Body: { institution_id: "{non_existent_uuid}", ... }
→ 400 or FK violation
```
**Why:** FK constraint on `app_user.institution_id`.

### FD-05: Activate with expired invite token
```
POST /api/auth/activate
Body: { invite_token: "{expired_jwt}", password: "..." }
→ 400 "Invalid invite token"
```
**Why:** JWT verification fails — token expired.

### FD-06: Activate already-active user
```
POST /api/auth/activate
Body: { invite_token: "{valid_jwt_for_active_user}", password: "..." }
→ 400 "User is already active"
```
**Why:** Activate checks `lifecycle_status == "active"` before proceeding.

---

## 5. Authentication Failures

### FA-01: Login with wrong password
```
POST /api/auth/login
Body: { email: "user@greenwood.com", password: "wrong" }
→ 401 "Invalid email or password"
```
**Why:** Supabase Auth rejects credentials.

### FA-02: Login with non-existent email
```
POST /api/auth/login
Body: { email: "nonexistent@greenwood.com", password: "..." }
→ 401 "Invalid email or password"
```
**Why:** Supabase Auth rejects — same error as wrong password (no user enumeration).

### FA-03: Request with expired JWT
```
GET /api/v1/users
Authorization: Bearer {expired_jwt}
→ 401 "Token expired"
```
**Why:** JWT verification fails — token expired.

### FA-04: Request with no JWT
```
GET /api/v1/users
→ 401 "Not authenticated"
```
**Why:** Protected endpoint requires valid JWT.

### FA-05: Request with malformed JWT
```
GET /api/v1/users
Authorization: Bearer "not-a-jwt"
→ 401 "Invalid token"
```
**Why:** JWT verification fails — malformed token.

---

## 6. Profile-Specific Failures

### FP-01: Create duplicate profile
```
POST /api/v1/users/{user_id}/profile
Body: { ... }
→ 400 "User already has a profile"
```
**Why:** Unique constraint on `user_profile.user_id` — one profile per user.

### FP-02: Teacher tries to update another teacher's profile
```
PATCH /api/v1/users/{other_teacher_id}/profile
Authorization: Bearer {teacher_token}
→ 403 "Permission denied"
```
**Why:** Teacher has NO `user_profile.admin`. Stage 3 bypass only works for own profile.

### FP-03: Student tries to create profile for another user
```
POST /api/v1/users/{other_user_id}/profile
Authorization: Bearer {student_token}
→ 403 "Permission denied"
```
**Why:** Student has NO `user_profile.admin`. Stage 3 bypass only works for own profile.

---

## 7. RLS Failures

### FRL-01: User sees empty list when no data in their scope
```
GET /api/v1/users
Authorization: Bearer {teacher_token_at_school_b}
→ 200 [] (empty — teacher at School B can't see School A's users)
```
**Why:** RLS filters by `institution_id`. Different institution = invisible.

### FRL-02: User gets 404 for resource in another scope
```
GET /api/v1/users/{user_from_other_institution}
Authorization: Bearer {teacher_token}
→ 404 (RLS filters out — user not visible)
```
**Why:** RLS filters by `institution_id`. Other institution's users return 404 (not 403 — no information leakage).
