# Journey 01 — Platform Owner

> **Role:** platform_owner
> **Scope:** Any (code bypass — all Casbin checks skipped)
> **Auth:** Custom HS256 JWT with `is_platform_owner: true`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Body: { email: "platform@school-erp.com", password: "..." }
→ 200 { access_token, is_platform_owner: true }
```

### HP-02: Create Client
```
POST /api/v1/platform/clients
Body: { slug: "greenwood", display_name: "Greenwood Academy", ... }
→ 201 { id, slug, display_name, current_lifecycle_status: "prospective" }
```

### HP-03: Transition Client Lifecycle
```
POST /api/v1/platform/clients/{client_id}/transition
Body: { new_state: "active", reason: "Contract signed" }
→ 200 { id, current_lifecycle_status: "active" }
```

### HP-04: Create Institution Type
```
POST /api/v1/platform/institution-types
Body: { code: "SCHOOL", name_id: "..." }
→ 201 { id, code }
```

### HP-05: Create Client Director (bootstrap)
```
POST /api/v1/platform/clients/{client_id}/users
Body: { email: "director@greenwood.com", name: "Greenwood Director", role_id: "...", user_category_id: "..." }
→ 201 { user: { id, email }, invite_url: "https://.../activate?token=..." }
```

### HP-06: List All Clients
```
GET /api/v1/platform/clients
→ 200 [{ id, slug, display_name, current_lifecycle_status }, ...]
```

### HP-07: Read Config Keys
```
GET /api/v1/config/keys
→ 200 [{ key, type, default_value, ... }, ...]
```

### HP-08: Create Config Key
```
POST /api/v1/config/keys
Body: { key: "homework.lateSubmissionPolicy", type: "json", default_value: "..." }
→ 201 { key, type, default_value }
```

### HP-09: Update Config Value
```
PATCH /api/v1/config/values/{value_id}
Body: { value: "new_value" }
→ 200 { id, key, value }
```

### HP-10: Transfer Ownership
```
POST /api/v1/platform/ownership-transfers
Body: { institution_id: "...", to_client_id: "...", reason: "..." }
→ 201 { approval_id, status: "pending" }
```

### HP-11: Approve Ownership Transfer
```
POST /api/v1/platform/ownership-transfers/{approval_id}/approve
Body: { consent_source: true, consent_dest: true, reason: "..." }
→ 200 { status: "approved" }
```

### HP-12: List Institution Types
```
GET /api/v1/platform/institution-types
→ 200 [{ id, code, name }, ...]
```

---

## Failure Scenarios

### FS-01: PO tries to list institution users (should fail — no institution context)
```
GET /api/v1/users
Authorization: Bearer {po_token}
→ 200 [] (empty — PO has no institution_id, RLS filters out everything)
```
**Why:** PO has `is_platform_owner=true` but `institution_id=None`. RLS returns empty set.

### FS-02: PO tries to create institution (should fail — no client context)
```
POST /api/v1/institutions
Authorization: Bearer {po_token}
Body: { display_name: "Test", institution_type_id: "..." }
→ 400 "Client not resolved from subdomain"
```
**Why:** PO accesses via platform URL (no subdomain). `ctx.client_id` is None.

### FS-03: PO tries to create user (should fail — no institution context)
```
POST /api/v1/users
Authorization: Bearer {po_token}
Body: { email: "test@test.com", name: "Test", user_category_id: "...", institution_id: "..." }
→ 403 "Permission denied" (Casbin: PO has no `user.create` in role_permission)
```
**Why:** PO's permissions are only config-related. User management is scoped to institutions.

### FS-04: Non-PO tries to access platform endpoints
```
POST /api/v1/platform/clients
Authorization: Bearer {cd_token}
→ 403 (require_platform_owner dependency rejects)
```
**Why:** Platform routes require `require_platform_owner` which checks `is_platform_owner`.

### FS-05: PO tries to transition another client's lifecycle (should work — PO has wildcard)
```
POST /api/v1/platform/clients/{other_client_id}/transition
Authorization: Bearer {po_token}
Body: { new_state: "suspended", reason: "Policy violation" }
→ 200 (PO has `*.*` at `any` scope — Casbin allows everything)
```
**Note:** This SHOULD work. PO is the highest authority.
