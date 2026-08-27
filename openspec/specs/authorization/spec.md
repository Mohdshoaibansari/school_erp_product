# Spec Delta — Authorization (MODIFIED)

> **Change:** add-c05-academic-structure
> **Domain:** authorization
> **Impact:** MODIFIED (new permissions)
> **Source:** `docs/architecture/adr-c05-academic-structure-implementation.md`

---

## ADDED Requirements

### REQ-AUTHZ-AC-01: Academic Structure Permissions

Add10 new permissions for C-05 academic structure management.

| Permission | Description | Default Roles |
|---|---|---|
| `academic_year.create` | Create academic year | Admin, institution_admin |
| `academic_year.read` | Read academic year | All roles |
| `academic_year.update` | Update academic year | Admin, institution_admin |
| `academic_year.transition` | Transition lifecycle | Admin, institution_admin |
| `enrollment.create` | Enroll student in section | Admin, institution_admin |
| `enrollment.read` | Read enrollments | All roles |
| `enrollment.update` | Transfer student | Admin, institution_admin |
| `teacher_assignment.create` | Assign teacher to subject | Admin, institution_admin |
| `teacher_assignment.read` | Read teacher assignments | All roles |
| `teacher_assignment.update` | Update teacher assignment | Admin, institution_admin |

**Rules:**
- Permissions seeded in Alembic migration
- Role-permission mappings for Admin, institution_admin, Principal, HOD, Teacher, Student
- C-04 remains the single source of truth (Non-Negotiable Rule 3)

---
<!-- Synced from add-c02-identity-person-model-revamp delta spec -->
## Person-Model Revamp — Authorization (Q8 Resolved)

> **Q8 RESOLVED as D3f:** `person` and `user_account` coexist. `role_assignment.user_id` SHALL target `user_account.id` (UNCHANGED). Roles are account-scoped (D8 + D3b); `person` and `user_account` coexist (D3f). The Casbin loader query text is unchanged. No further delta is needed in this domain.

### REQ-AUTHZ-Q8-01: role_assignment.user_id Referent (Resolved — D3f, no change needed)

`role_assignment.user_id` SHALL target `user_account.id` (UNCHANGED). The Casbin loader query text is unchanged.

#### Scenario: role_assignment referent unchanged (confirmed)
- **WHEN** the `role_assignment` FK and Casbin loader are inspected
- **THEN** `role_assignment.user_id` SHALL reference `user_account.id`
- **AND** the Casbin loader query SHALL be unchanged
- **AND** no authz policy, permission, or role-definition change SHALL result from this revamp
