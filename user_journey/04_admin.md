# Journey 04 — Admin

> **Role:** Admin
> **Scope:** Own institution — `institution_id` must match
> **Auth:** Supabase JWT with `user_tier: "institution"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "admin@greenwoodhigh.com", password: "..." }
→ 200 { access_token, user_tier: "institution", client_id: "..." }
```

### HP-02: Create User (Teacher)
```
POST /api/v1/users
Body: { email: "teacher@greenwoodhigh.com", name: "Teacher", user_category_id: "...", institution_id: "...", role_id: "..." }
→ 201 { user: { id }, invite_url: "..." }
```

### HP-03: List Users
```
GET /api/v1/users
→ 200 [{ id, email, name, lifecycle_status }, ...]
```

### HP-04: Suspend User
```
POST /api/v1/users/{user_id}/transition
Body: { new_state: "suspended", reason: "Policy violation" }
→ 200 { id, lifecycle_status: "suspended" }
```

### HP-05: Create Fee Type
```
POST /api/v1/fee-types
Body: { name: "Tuition", institution_id: "...", default_amount: 50000 }
→ 201 { id, name }
```

### HP-06: Assign Fee
```
POST /api/v1/fee-assignments
Body: { fee_type_id: "...", user_ids: ["..."], amount: 50000, institution_id: "..." }
→ 201 [{ id }]
```

### HP-07: Record Payment
```
POST /api/v1/payments
Body: { fee_assignment_id: "...", amount: 30000, payment_method: "Bank Transfer" }
→ 201 { id, receipt_number }
```

### HP-08: Create Profile for Any User
```
POST /api/v1/users/{user_id}/profile
Body: { date_of_birth: "1990-01-01", gender: "female" }
→ 201 { id }
```

### HP-09: Update Any User's Profile
```
PATCH /api/v1/users/{user_id}/profile
Body: { blood_group: "O+" }
→ 200 { id }
```

### HP-10: Create Role Assignment
```
POST /api/v1/users/{user_id}/roles
Body: { role_id: "..." }
→ 201 { id }
```

### HP-11: Delete Role Assignment
```
DELETE /api/v1/users/{user_id}/roles/{assignment_id}
→ 204
```

### HP-12: Read Config Values
```
GET /api/v1/config/values
→ 200 [{ id, key, value }, ...]
```

### HP-13: Update Config Value
```
PATCH /api/v1/config/values/{value_id}
Body: { value: "new_value" }
→ 200 { id, value }
```

---

## Failure Scenarios

### FS-01: Admin tries to create institution
```
POST /api/v1/institutions
Authorization: Bearer {admin_token}
→ 403 "Permission denied"
```
**Why:** Admin has `institution.read/update/transition_lifecycle` but NOT `institution.create`.

### FS-02: Admin tries to access another institution's data
```
GET /api/v1/users
Host: other-school.localhost
Authorization: Bearer {admin_token}
→ 403 "Access denied. Account does not belong to this client."
```
**Why:** Login cross-tenant check fails.

### FS-03: Admin tries to manage platform config
```
POST /api/v1/config/keys
Authorization: Bearer {admin_token}
Body: { key: "new.key", ... }
→ 403 "Permission denied"
```
**Why:** Admin has `config.value.*` but NOT `config.key.create`.

### FS-04: Admin tries to delete user
```
DELETE /api/v1/users/{user_id}
Authorization: Bearer {admin_token}
→ 403 "Permission denied"
```
**Why:** Admin has `user.create/read/update/suspend` but NOT `user.delete`.

### FS-05: Admin tries to manage org units (has permission)
```
POST /api/v1/org-units
Authorization: Bearer {admin_token}
Body: { ... }
→ 201 (Admin has `org_unit.create`)
```
**Note:** This SHOULD succeed.
