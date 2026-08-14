# Journey 03 — Institution Admin

> **Role:** institution_admin
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

### HP-02: Read Own Institution
```
GET /api/v1/institutions/{inst_id}
→ 200 { id, display_name, current_lifecycle_status }
```

### HP-03: Update Institution
```
PATCH /api/v1/institutions/{inst_id}
Body: { display_name: "Greenwood High School - Updated" }
→ 200 { id, display_name }
```

### HP-04: Create Org Unit
```
POST /api/v1/org-units
Body: { institution_id: "...", name: "Science Wing", type_id: "...", sort_order: 1 }
→ 201 { id, name }
```

### HP-05: Move Org Unit
```
POST /api/v1/org-units/{ou_id}/move
Body: { new_parent_id: "..." }
→ 200 { id, parent_id }
```

### HP-06: Archive Org Unit
```
POST /api/v1/org-units/{ou_id}/archive
→ 200 { id, current_lifecycle_status: "archived" }
```

### HP-07: Reactivate Org Unit
```
POST /api/v1/org-units/{ou_id}/reactivate
→ 200 { id, current_lifecycle_status: "active" }
```

### HP-08: Update Own Profile
```
PATCH /api/v1/users/{admin_id}/profile
Body: { photo: "https://..." }
→ 200 { id, photo }
```

### HP-09: Create Profile for Student
```
POST /api/v1/users/{student_id}/profile
Body: { date_of_birth: "2014-07-15", gender: "male" }
→ 201 { id, user_id }
```

---

## Failure Scenarios

### FS-01: Institution Admin tries to create institution
```
POST /api/v1/institutions
Authorization: Bearer {inst_admin_token}
Body: { display_name: "New School", ... }
→ 403 "Permission denied"
```
**Why:** `institution_admin` has `institution.read/update` but NOT `institution.create`.

### FS-02: Institution Admin tries to create user
```
POST /api/v1/users
Authorization: Bearer {inst_admin_token}
Body: { email: "teacher@test.com", ... }
→ 403 "Permission denied"
```
**Why:** `institution_admin` has no `user.create` permission.

### FS-03: Institution Admin tries to manage fees
```
POST /api/v1/fee-types
Authorization: Bearer {inst_admin_token}
Body: { name: "Fee", ... }
→ 403 "Permission denied"
```
**Why:** `institution_admin` has no `fee.create` permission.

### FS-04: Institution Admin tries to access another institution
```
GET /api/v1/institutions/{other_inst_id}
Authorization: Bearer {inst_admin_token}
→ 404 (RLS filters out other institution)
```
**Why:** RLS filters by `institution_id` — other institutions are invisible.

### FS-05: Institution Admin tries to transition institution lifecycle
```
POST /api/v1/institutions/{inst_id}/transition
Body: { new_state: "active" }
→ 403 "Permission denied"
```
**Why:** `institution_admin` has `institution.update` but NOT `institution.transition_lifecycle`.

### FS-06: Institution Admin tries to read another user's profile
```
GET /api/v1/users/{other_user_id}/profile
Authorization: Bearer {inst_admin_token}
→ 200 (admin can read any profile via `user_profile.admin`)
```
**Note:** This SHOULD succeed — `institution_admin` has `user_profile.admin` with institution scope.
