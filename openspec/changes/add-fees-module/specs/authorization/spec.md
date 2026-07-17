# Authorization — MODIFIED Requirements (Fees Module)

> **Domain:** `authorization`  
> **Classification:** MODIFIED  
> **Change:** Add 11 fee-related permissions + ~17 role-permission mappings to C-04's tables.  
> **C-04 code changes:** None (DB-only — C-04's on_startup auto-loads).

---

## MOD-FR-1: Permission Catalog Extension

### MOD-FR-1.1: Add 11 fee-related permission rows

The `permission` table is extended with:

| name | resource | action |
|---|---|---|
| `fee.read` | fee | read |
| `fee.create` | fee | create |
| `fee.update` | fee | update |
| `fee.delete` | fee | delete |
| `fee_assignment.read` | fee_assignment | read |
| `fee_assignment.create` | fee_assignment | create |
| `fee_assignment.update` | fee_assignment | update |
| `fee_assignment.waive` | fee_assignment | waive |
| `payment.read` | payment | read |
| `payment.create` | payment | create |
| `receipt.read` | receipt | read |

**Acceptance:**
- Migration inserts 11 rows with `ON CONFLICT (name) DO NOTHING`.
- `permission` table grows from 26 to 37 rows.

### MOD-FR-1.2: Add role-permission mappings

The `role_permission` table is extended with ~17 rows mapping roles to fee permissions:

| Role | Permissions |
|---|---|
| Admin | All 11 |
| Principal | fee.read, fee_assignment.read, payment.read, receipt.read |
| HOD | fee_assignment.read, payment.read |
| Teacher | fee_assignment.read |
| Staff | fee_assignment.read |
| Student | fee_assignment.read, payment.read |

**Acceptance:**
- Migration inserts ~17 rows with `ON CONFLICT (role_id, permission_id) DO NOTHING`.
- `role_permission` table grows from ~40 to ~57 rows.

### MOD-FR-1.3: C-04 auto-loads new policies

C-04's `on_startup` reads all `role_permission` rows. New rows are automatically included.

**Acceptance:**
- No C-04 code change required.
- After restart, Casbin enforcer includes fee policies.
- Existing C-04 tests pass unchanged.
