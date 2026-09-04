# Impact Classification — C-06 Relationship Management Framework

> **Capability:** C-06 Relationship Management Framework
> **Status:** Draft
> **Last updated:** 2026-09-03
> **Source:** `docs/prd/C-06-Relationship-Management-Framework-PRD.md`, grill session 2026-09-03

---

## 1. Impact Summary

C-06 is a **new kernel capability** that provides a centralized person-to-person relationship model with typed, temporal relationships and relationship-specific responsibilities. This is a greenfield implementation — no production data to preserve.

| Impact Type | Count |
|---|---|
| **ADDED** (new tables) | 5 new tables |
| **MODIFIED** (existing tables) | 0 tables modified |
| **REMOVED** (deprecated tables) | 0 tables removed |
| **CROSS-CUTTING** (multiple domains) | 2 capabilities affected |

---

## 2. Key Design Decisions (from Grill Session)

| # | Decision | Rationale |
|---|---|---|
| D1 | Relationships have `client_id` only (no `institution_id`) | Tenant isolation via RLS; institution context derived from Person |
| D2 | Seed default RelationshipTypes in migration | Mother, Child, Father, Guardian, Sibling, Grandparent, Foster Parent, Step Parent with inverse pairs |
| D3 | Seed default ContactRoles in migration | PrimaryGuardian, Guardian, FinancialResponsible, EmergencyContact, PickupAuthorized |
| D4 | Seed compatibility matrix | Which ContactRoles are valid for which RelationshipTypes |
| D5 | Symmetric normalization: `person_a_id < person_b_id` | UUID comparison ensures unordered uniqueness |
| D6 | App-level temporal overlap validation | No PostgreSQL exclusion constraints |
| D7 | `normalized_pair` column for unordered uniqueness | `LEAST(person_a_id, person_b_id) || GREATEST(person_a_id, person_b_id)` |
| D8 | Dynamic status computation (no `status` column) | Future/Effective/Historical derived from dates |
| D9 | Service-level containment enforcement | Role validity contained within Relationship validity |
| D10 | Service-level RelationshipType change validation | Reject if existing roles incompatible with new type |
| D11 | Auto-generate inverse RelationshipType | API accepts single type, service creates pair |
| D12 | Module at `kernel/relationship/` (singular) | Matches existing conventions |
| D13 | No priority field on ContactRoleAssignment | Deferred to future enhancement |
| D14 | Integrate with existing AuditEmitter | Emit events for all mutations |

---

## 3. Table Changes

### 3.1 Tables to CREATE (5)

#### `relationship_type`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `client_id` | UUID | FK → client.id, NOT NULL | Tenant isolation |
| `code` | VARCHAR(100) | UNIQUE, NOT NULL | e.g., "mother", "child", "sibling" |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `inverse_relationship_type_id` | UUID | FK → relationship_type.id, NULLABLE | Self-referential; NULL for symmetric types |
| `is_symmetric` | BOOLEAN | NOT NULL, DEFAULT false | True for Sibling-type relationships |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Rules:**
- Semantic fields (code, name, inverse, is_symmetric) are immutable after creation
- Non-symmetric type MUST have inverse
- Inverse pair created transactionally

#### `contact_role`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `client_id` | UUID | FK → client.id, NOT NULL | Tenant isolation |
| `code` | VARCHAR(100) | UNIQUE, NOT NULL | e.g., "primary_guardian", "financial_responsible" |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

#### `relationship_type_contact_role` (compatibility matrix)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `relationship_type_id` | UUID | FK → relationship_type.id, NOT NULL | |
| `contact_role_id` | UUID | FK → contact_role.id, NOT NULL | |

**Constraints:**
- `UNIQUE(relationship_type_id, contact_role_id)`
- Composite PK

#### `relationship`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `client_id` | UUID | FK → client.id, NOT NULL | Tenant isolation |
| `person_a_id` | UUID | FK → person.id, NOT NULL | First person |
| `person_b_id` | UUID | FK → person.id, NOT NULL | Second person |
| `relationship_type_id` | UUID | FK → relationship_type.id, NOT NULL | |
| `valid_from` | DATE | NOT NULL | Start of relationship |
| `valid_to` | DATE | NULLABLE | End of relationship; NULL = ongoing |
| `normalized_pair` | VARCHAR(255) | UNIQUE, NOT NULL | `LEAST(person_a_id, person_b_id) \|\| GREATEST(person_a_id, person_b_id)` |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraints:**
- `person_a_id != person_b_id` (CHECK)
- `valid_to IS NULL OR valid_to >= valid_from` (CHECK)
- `normalized_pair` UNIQUE prevents unordered duplicates

**Status (computed dynamically):**
- Future: `today < valid_from`
- Effective: `valid_from <= today AND (valid_to IS NULL OR today <= valid_to)`
- Historical: `valid_to IS NOT NULL AND today > valid_to`

#### `contact_role_assignment`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `client_id` | UUID | FK → client.id, NOT NULL | Tenant isolation |
| `relationship_id` | UUID | FK → relationship.id, NOT NULL | |
| `contact_role_id` | UUID | FK → contact_role.id, NOT NULL | |
| `valid_from` | DATE | NOT NULL | Start of role assignment |
| `valid_to` | DATE | NULLABLE | End of role assignment; NULL = ongoing |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraints:**
- `valid_to IS NULL OR valid_to >= valid_from` (CHECK)

**Rules (enforced at service level):**
- Role validity must be contained within parent Relationship validity
- Same-role periods may not overlap for the same Relationship
- Historical assignments preserved (no hard delete)

---

## 4. Entity Relationship Summary

```
                    RelationshipType
                         │
                         │ (inverse self-ref)
                         │
Person A ─────► Relationship ◄───── Person B
                         │
                         ▼
               ContactRoleAssignment
                         │
                         ▼
                    ContactRole
```

---

## 5. Business Invariants

| # | Invariant | Enforcement |
|---|---|---|
| 1 | Person cannot be related to themselves | DB CHECK (`person_a_id != person_b_id`) |
| 2 | Unordered person pair uniqueness | DB UNIQUE (`normalized_pair`) |
| 3 | No overlapping Relationship periods for same pair | App level validation |
| 4 | Non-symmetric RelationshipType has inverse | App level validation |
| 5 | Inverse pair created transactionally | App level (single transaction) |
| 6 | Symmetric types normalized (`person_a_id < person_b_id`) | App level |
| 7 | ContactRole compatibility is explicit allow-list | App level |
| 8 | Role validity contained within Relationship validity | App level |
| 9 | Same-role periods may not overlap | App level |
| 10 | RelationshipType change validates existing roles | App level |
| 11 | Relationship date changes protect child roles | App level |
| 12 | Historical data preserved (no hard delete) | App level |
| 13 | Tenant boundaries respected (client_id) | DB RLS |

---

## 6. New Permissions (C-04)

| Permission | Description | Default Roles |
|---|---|---|
| `relationship.create` | Create relationship | Admin, institution_admin |
| `relationship.read` | Read relationships | All roles |
| `relationship.update` | Update relationship | Admin, institution_admin |
| `relationship.end` | End relationship | Admin, institution_admin |
| `relationship.change_type` | Change relationship type | Admin, institution_admin |
| `relationship_type.create` | Create relationship type | Platform admin only |
| `relationship_type.read` | Read relationship types | All roles |
| `contact_role.read` | Read contact roles | All roles |
| `contact_role_assignment.create` | Add contact role to relationship | Admin, institution_admin |
| `contact_role_assignment.update` | Update contact role period | Admin, institution_admin |
| `contact_role_assignment.end` | End contact role | Admin, institution_admin |

---

## 7. RLS Policies

All C-06 tables carry `client_id` for tenant isolation:

```sql
-- Same pattern as existing tables
CREATE POLICY <table>_sel ON <table> FOR SELECT USING (
  is_platform_owner() OR client_id = current_client_id()
);
CREATE POLICY <table>_ins ON <table> FOR INSERT WITH CHECK (
  is_platform_owner() OR client_id = current_client_id()
);
CREATE POLICY <table>_upd ON <table> FOR UPDATE USING (
  is_platform_owner() OR client_id = current_client_id()
);
CREATE POLICY <table>_del ON <table> FOR DELETE USING (
  is_platform_owner() OR client_id = current_client_id()
);
```

Tables: `relationship_type`, `contact_role`, `relationship_type_contact_role`, `relationship`, `contact_role_assignment`

---

## 8. Cross-Cutting Impacts

### 8.1 Identity & User (C-02)

| Impact | Details |
|---|---|
| References Person | `person_a_id` and `person_b_id` FK to `person.id` |
| No schema changes | C-02 tables unchanged |

### 8.2 Authorization (C-04)

| Impact | Details |
|---|---|
| New permissions | 11 new permissions for relationship management |
| Role assignments | Admin and institution_admin get relationship permissions |
| Casbin policies | New policies for relationship entities |

### 8.3 Audit (C-11)

| Impact | Details |
|---|---|
| AuditEmitter integration | Emit events for all relationship mutations |
| Events | relationship.created, updated, ended, type_changed, contact_role_added, updated, ended |

---

## 9. Seeded Data

### 9.1 Default RelationshipTypes

| Code | Name | Inverse | Is Symmetric |
|---|---|---|---|
| `mother` | Mother | `child` | false |
| `child` | Child | `mother` | false |
| `father` | Father | `child` | false |
| `guardian` | Guardian | `child` | false |
| `sibling` | Sibling | `sibling` | true |
| `grandparent` | Grandparent | `grandchild` | false |
| `grandchild` | Grandchild | `grandparent` | false |
| `foster_parent` | Foster Parent | `foster_child` | false |
| `foster_child` | Foster Child | `foster_parent` | false |
| `step_parent` | Step Parent | `step_child` | false |
| `step_child` | Step Child | `step_parent` | false |

### 9.2 Default ContactRoles

| Code | Name |
|---|---|
| `primary_guardian` | Primary Guardian |
| `guardian` | Guardian |
| `financial_responsible` | Financial Responsible |
| `emergency_contact` | Emergency Contact |
| `pickup_authorized` | Pickup Authorized |

### 9.3 Default Compatibility Matrix

| RelationshipType | Allowed ContactRoles |
|---|---|
| `mother` | primary_guardian, guardian, financial_responsible, emergency_contact, pickup_authorized |
| `father` | primary_guardian, guardian, financial_responsible, emergency_contact, pickup_authorized |
| `guardian` | primary_guardian, guardian, financial_responsible, emergency_contact, pickup_authorized |
| `grandparent` | guardian, emergency_contact, pickup_authorized |
| `foster_parent` | primary_guardian, guardian, financial_responsible, emergency_contact, pickup_authorized |
| `step_parent` | guardian, emergency_contact, pickup_authorized |
| `sibling` | emergency_contact |
| `child` | (none — inverse perspective) |
| `grandchild` | (none — inverse perspective) |
| `foster_child` | (none — inverse perspective) |
| `step_child` | (none — inverse perspective) |

---

## 10. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/relationship-types` | List relationship types |
| POST | `/api/v1/relationship-types` | Create relationship type (auto-generates inverse) |
| GET | `/api/v1/contact-roles` | List contact roles |
| GET | `/api/v1/people/{person_id}/relationships` | List relationships for a person |
| POST | `/api/v1/people/{person_id}/relationships` | Create relationship |
| GET | `/api/v1/relationships/{id}` | Get relationship details |
| PATCH | `/api/v1/relationships/{id}` | Update relationship (dates, type) |
| POST | `/api/v1/relationships/{id}/end` | End relationship |
| POST | `/api/v1/relationships/{id}/contact-roles` | Add contact role to relationship |
| PATCH | `/api/v1/contact-role-assignments/{id}` | Update contact role period |
| POST | `/api/v1/contact-role-assignments/{id}/end` | End contact role |

---

## 11. Service Layer

### RelationshipService

- `create_relationship()` — Create relationship with optional initial roles
- `get_relationship()` — Get relationship by ID
- `update_relationship()` — Update dates or type
- `end_relationship()` — End relationship (set valid_to)
- `change_relationship_type()` — Change type with role validation
- `list_relationships()` — List relationships for a person
- `get_inverse_view()` — Get inverse perspective
- `resolve_related_persons()` — Get related Person records

### RelationshipTypeService

- `create_inverse_pair()` — Create type with auto-generated inverse
- `get_type()` — Get type by ID
- `list_types()` — List all types
- `validate_contact_role()` — Validate role compatibility

### ContactRoleService

- `list_roles()` — List all contact roles
- `list_compatible_roles()` — List roles compatible with a RelationshipType

### ContactRoleAssignmentService

- `add_role()` — Add role to relationship
- `update_role_period()` — Update role validity
- `end_role()` — End role assignment
- `list_effective_roles()` — List currently effective roles
- `list_historical_roles()` — List historical roles

---

## 12. Migration Plan

### 12.1 Alembic Migration (026)

1. Create C-06 tables (5 tables)
2. Seed default RelationshipTypes with inverse pairs
3. Seed default ContactRoles
4. Seed compatibility matrix
5. Add RLS policies for all C-06 tables
6. Seed permissions in `permission` and `role_permission`

### 12.2 Rollback Plan

- C-06 tables are new — drop on rollback
- Permissions are soft-deleted on rollback

---

## 13. Testing Strategy

| Test Type | Scope |
|---|---|
| Unit tests | Relationship CRUD, temporal validation, symmetric normalization, inverse resolution |
| Unit tests | ContactRole compatibility, containment, overlap prevention |
| Unit tests | RelationshipType change validation |
| Integration tests | API/service/database interaction, RLS, authorization, tenant isolation |
| Concurrency tests | Concurrent duplicate relationship prevention |

---

## 14. Effort Estimate

| Component | Estimate |
|---|---|
| C-06 models + repos | 2 days |
| C-06 services (relationship, type, role assignment) | 3 days |
| C-06 routes + DTOs | 2 days |
| C-06 permissions + RLS | 1 day |
| Audit integration | 0.5 day |
| Tests | 2 days |
| Documentation + verification | 0.5 day |
| **Total** | **~11 days** |

---

## 15. Deferred Items

The following are explicitly out of scope for Phase 1:

| Item | Reason |
|---|---|
| Priority ordering for EmergencyContact | Deferred to future enhancement |
| Institution-specific RelationshipType customization | Phase 2 |
| Institution-specific ContactRole customization | Phase 2 |
| Cross-institution relationship linking | Phase 2 |
| Advanced family graph queries | Phase 2 |
| Household entities | Phase 2 |
| Custody/legal-document modeling | Phase 2 |
| Approval workflows | Phase 2 |

---

## 16. Business Module Integration

C-06 is the single source of truth for person-to-person relationships. The following modules will consume C-06:

| Module | Usage |
|---|---|
| Student | Resolve parents and guardians |
| Parent | Discover related children |
| Fees | Resolve FinancialResponsible |
| Communication | Relationship-based recipient resolution |
| Transport | Resolve PickupAuthorized |
| Attendance | Parent/guardian notification resolution |
| Health | Authorized guardian/contact resolution |

**No consumer module may maintain a duplicate relationship table for the same business fact.**
