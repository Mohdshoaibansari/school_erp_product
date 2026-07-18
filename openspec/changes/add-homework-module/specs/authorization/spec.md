# Authorization — MODIFIED Requirements (Homework Module)

> **Domain:** `authorization`  
> **Classification:** MODIFIED  
> **Change:** Add 10 homework-related permissions + ~15 role-permission mappings to C-04's tables.  
> **C-04 code changes:** None (DB-only — C-04's on_startup auto-loads).

---

## MOD-FR-1: Permission Catalog Extension

### MOD-FR-1.1: Add 10 homework-related permission rows

The `permission` table is extended with:

| name | resource | action |
|---|---|---|
| `homework.read` | homework | read |
| `homework.create` | homework | create |
| `homework.update` | homework | update |
| `homework.delete` | homework | delete |
| `homework.close` | homework | close |
| `submission.read` | submission | read |
| `submission.create` | submission | create |
| `grade.read` | grade | read |
| `grade.create` | grade | create |
| `grade.update` | grade | update |

**Acceptance:**
- Migration inserts 10 rows with `ON CONFLICT (name) DO NOTHING`.
- `permission` table grows from 37 to 47 rows.

### MOD-FR-1.2: Add role-permission mappings

| Role | Permissions |
|---|---|
| Admin | homework.read, submission.read, grade.read |
| Principal | homework.read, submission.read, grade.read |
| HOD | homework.read, submission.read, grade.read |
| Teacher | homework.read/create/update/delete/close, submission.read, grade.read/create/update |
| Student | homework.read, submission.read, submission.create, grade.read |
| Staff | (none) |

**Acceptance:**
- Migration inserts ~15 rows with `ON CONFLICT (role_id, permission_id) DO NOTHING`.
- `role_permission` table grows from ~57 to ~72 rows.
- C-04's `on_startup` auto-loads new rows at next restart.
- Existing C-04 tests pass unchanged.
