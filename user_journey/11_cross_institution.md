# Journey 11 — Cross-institution

> **Role:** cross_institution
> **Scope:** Own client (tenant) — read-only oversight across institutions
> **Auth:** Supabase JWT with `user_tier: "institution"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "regional@greenwood.com", password: "..." }
→ 200 { access_token }
```

### HP-02: Read Client Info
```
GET /api/v1/clients/{client_id}
→ 200 { id, slug, display_name }
```

### HP-03: List Institutions (cross-institution)
```
GET /api/v1/institutions?cross_institution=true
→ 200 [{ id, display_name }, ...] (all institutions under the client)
```

### HP-04: Read Institution
```
GET /api/v1/institutions/{inst_id}
→ 200 { id, display_name, current_lifecycle_status }
```

### HP-05: List Org Units (cross-institution)
```
GET /api/v1/org-units?institution_id={inst_id}&cross_institution=true
→ 200 [{ id, name, type_id }, ...]
```

### HP-06: Read Org Unit
```
GET /api/v1/org-units/{ou_id}
→ 200 { id, name, parent_id }
```

---

## Failure Scenarios

### FS-01: Cross-institution tries to create institution
```
POST /api/v1/institutions
Authorization: Bearer {cross_inst_token}
→ 403 "Permission denied"
```
**Why:** `cross_institution` has only `client.read`, `institution.read`, `org_unit.read` — all read-only.

### FS-02: Cross-institution tries to update institution
```
PATCH /api/v1/institutions/{inst_id}
Authorization: Bearer {cross_inst_token}
→ 403 "Permission denied"
```
**Why:** No `institution.update` permission.

### FS-03: Cross-institution tries to create user
```
POST /api/v1/users
Authorization: Bearer {cross_inst_token}
→ 403 "Permission denied"
```
**Why:** No `user.*` permissions at all.

### FS-04: Cross-institution tries to manage org units
```
POST /api/v1/org-units
Authorization: Bearer {cross_inst_token}
→ 403 "Permission denied"
```
**Why:** No `org_unit.create` permission.

### FS-05: Cross-institution tries to manage fees
```
POST /api/v1/fee-assignments
Authorization: Bearer {cross_inst_token}
→ 403 "Permission denied"
```
**Why:** No `fee_assignment.*` permissions.

### FS-06: Cross-institution tries to access another client's data
```
GET /api/v1/institutions
Host: other-client.localhost
Authorization: Bearer {cross_inst_token}
→ 403 "Access denied. Account does not belong to this client."
```
**Why:** Login cross-tenant check fails.

---

## Notes

The `cross_institution` role is designed for **oversight roles** (Regional Manager, Group Academic Head, Finance Controller) who need read-only visibility across all institutions within a client. They cannot modify any data.
