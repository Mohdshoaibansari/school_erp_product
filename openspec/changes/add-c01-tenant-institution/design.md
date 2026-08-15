# Design Document: Capability C-01 Tenant & Institution Management

## 1. Overview & Architecture

This design document specifies the technical realization of **C-01 Tenant & Institution Management**. C-01 implements a hybrid isolation architecture where:
1. **Tenant-Aware Repositories** serve as the mandatory data access abstraction for application business logic.
2. **Postgres Row-Level Security (RLS)** acts as a defense-in-depth security backstop filtering by `client_id`.

```
                    ┌──────────────────────────────────────────────┐
                    │ Client Portal Subdomain (e.g. acme.school.com)│
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Tenant Context Middleware                    │
                    │  - Resolves client_id from subdomain        │
                    │  - Reads selected institution_id from JWT    │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Casbin AuthZ Middleware (C-04 Framework)     │
                    │  - Enforces D11 write-permission matrix      │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ C-01 Business Domain Services & Repositories │
                    │  - Injects client_id & default institution_id│
                    │  - Enforces OrgUnit cycle prevention         │
                    │  - Materializes InstitutionType templates    │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Postgres Database with RLS Backstop          │
                    │  - Hard fence: client_id RLS policies        │
                    │  - Self-visible policy on client table       │
                    └──────────────────────────────────────────────┘
```

## 2. Data Model & Schema Definitions

All primary keys use UUID v4 (`gen_random_uuid()`).

### 2.1 Lookup Tables

#### `legal_entity_type`
- `id` (UUID v4, PK)
- `name` (VARCHAR(100), UNIQUE, NOT NULL) — e.g. "Sole Proprietorship", "Private Limited", "Trust", "Society"

#### `org_unit_type`
- `id` (UUID v4, PK)
- `name` (VARCHAR(100), UNIQUE, NOT NULL) — e.g. "Faculty", "Department", "Grade", "Class", "Section"

#### `institution_type_name`
- `id` (UUID v4, PK)
- `name` (VARCHAR(100), UNIQUE, NOT NULL) — e.g. "School", "College", "University"

### 2.2 Core Entity Tables

#### `client`
- `id` (UUID v4, PK)
- `slug` (VARCHAR(63), UNIQUE, NOT NULL) — immutable, lowercase, `[a-z0-9-]`
- `display_name` (VARCHAR(255), NOT NULL)
- `legal_name` (VARCHAR(255), NOT NULL)
- `legal_entity_type_id` (UUID v4, FK → `legal_entity_type.id`, NOT NULL)
- `tax_registration_number` (VARCHAR(100), NULLABLE)
- `primary_contact_email` (VARCHAR(255), NOT NULL)
- `primary_contact_phone` (VARCHAR(50), NOT NULL)
- `billing_contact_email` (VARCHAR(255), NOT NULL)
- `address_id` (UUID v4, NULLABLE) — FK → C-13 Address
- `current_lifecycle_status` (VARCHAR(50), NOT NULL) — `Prospective`, `Active`, `Suspended`, `Archived`, `Terminated`
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `archived_at` (TIMESTAMPTZ, NULLABLE)

*RLS Policy on `client`:*
```sql
CREATE POLICY client_self_visible ON client
    FOR SELECT
    USING (id = auth.current_client_id() OR auth.is_platform_owner());
```

#### `institution_type`
- `id` (UUID v4, PK)
- `name_id` (UUID v4, FK → `institution_type_name.id`, NOT NULL)
- `code` (VARCHAR(50), UNIQUE, NOT NULL)
- `is_system` (BOOLEAN, NOT NULL, DEFAULT false)
- `default_org_unit_template` (JSONB, NOT NULL) — `{ org_unit_type: "...", sort_order: 1, children: [...] }`
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)

#### `institution`
- `id` (UUID v4, PK)
- `client_id` (UUID v4, FK → `client.id`, NOT NULL) — Tenant isolation key
- `institution_type_id` (UUID v4, FK → `institution_type.id`, NOT NULL) — Immutable after creation
- `display_name` (VARCHAR(255), NOT NULL)
- `legal_name` (VARCHAR(255), NULLABLE)
- `code` (VARCHAR(50), NULLABLE) — Within-client unique short code
- `primary_contact_email` (VARCHAR(255), NOT NULL)
- `primary_contact_phone` (VARCHAR(50), NOT NULL)
- `address_id` (UUID v4, NULLABLE) — FK → C-13 Address
- `current_lifecycle_status` (VARCHAR(50), NOT NULL) — `Onboarding`, `Active`, `Inactive`, `Archived`
- `established_year` (INTEGER, NULLABLE)
- `affiliation_number` (VARCHAR(100), NULLABLE)
- `affiliation_board` (VARCHAR(100), NULLABLE)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `archived_at` (TIMESTAMPTZ, NULLABLE)

*RLS Policy on `institution`:*
```sql
CREATE POLICY institution_client_isolation ON institution
    USING (client_id = auth.current_client_id() OR auth.is_platform_owner());
```

#### `org_unit`
- `id` (UUID v4, PK)
- `client_id` (UUID v4, FK → `client.id`, NOT NULL)
- `institution_id` (UUID v4, FK → `institution.id`, NOT NULL)
- `parent_id` (UUID v4, FK → `org_unit.id`, NULLABLE) — Nullable = root node
- `name` (VARCHAR(255), NOT NULL)
- `type_id` (UUID v4, FK → `org_unit_type.id`, NOT NULL) — Immutable after creation
- `sort_order` (INTEGER, NOT NULL, DEFAULT 0)
- `code` (VARCHAR(50), NULLABLE)
- `current_lifecycle_status` (VARCHAR(50), NOT NULL, DEFAULT 'active') — `active`, `inactive`, `archived`
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `archived_at` (TIMESTAMPTZ, NULLABLE)

*RLS Policy on `org_unit`:*
```sql
CREATE POLICY org_unit_client_isolation ON org_unit
    USING (client_id = auth.current_client_id() OR auth.is_platform_owner());
```

### 2.3 Lifecycle & Approval Tracking Tables

#### `approval`
- `id` (UUID v4, PK)
- `client_id` (UUID v4, FK → `client.id`, NULLABLE) — NULL for platform-level approvals
- `operation_type` (VARCHAR(100), NOT NULL) — `client_lifecycle`, `institution_lifecycle`, `ownership_transfer`
- `requested_by` (UUID v4, NOT NULL) — User ID
- `approved_by` (UUID v4, NULLABLE) — User ID
- `status` (VARCHAR(50), NOT NULL) — `pending`, `approved`, `denied`
- `details` (JSONB, NULLABLE)
- `requested_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `approved_at` (TIMESTAMPTZ, NULLABLE)

#### `client_lifecycle_events`
- `id` (UUID v4, PK)
- `client_id` (UUID v4, FK → `client.id`, NOT NULL)
- `approval_id` (UUID v4, FK → `approval.id`, NULLABLE)
- `from_status` (VARCHAR(50), NOT NULL)
- `to_status` (VARCHAR(50), NOT NULL)
- `reason` (TEXT, NOT NULL)
- `actor_id` (UUID v4, NOT NULL)
- `entered_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)

#### `institution_lifecycle_events`
- `id` (UUID v4, PK)
- `client_id` (UUID v4, FK → `client.id`, NOT NULL)
- `institution_id` (UUID v4, FK → `institution.id`, NOT NULL)
- `approval_id` (UUID v4, FK → `approval.id`, NULLABLE)
- `from_status` (VARCHAR(50), NOT NULL)
- `to_status` (VARCHAR(50), NOT NULL)
- `reason` (TEXT, NOT NULL)
- `actor_id` (UUID v4, NOT NULL)
- `entered_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)

#### `ownership_transfer_events`
- `id` (UUID v4, PK)
- `from_client_id` (UUID v4, FK → `client.id`, NOT NULL)
- `to_client_id` (UUID v4, FK → `client.id`, NOT NULL)
- `institution_id` (UUID v4, FK → `institution.id`, NOT NULL)
- `approval_id` (UUID v4, FK → `approval.id`, NOT NULL)
- `approved_by` (UUID v4, NOT NULL)
- `consent_source` (BOOLEAN, NOT NULL, DEFAULT false)
- `consent_dest` (BOOLEAN, NOT NULL, DEFAULT false)
- `transferred_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `reason` (TEXT, NOT NULL)

## 3. API Specifications

APIs are subdomain-resolved: `/api/v1/...` implicitly operates under the Client resolved from the subdomain. Platform Owner APIs live under `/api/v1/platform/...`.

### 3.1 Subdomain-Resolved Endpoints

- `GET /api/v1/client/self`
  - Returns current Client details for authorized users.
- `GET /api/v1/institutions`
  - Returns list of Institutions under current Client (filtered by user institution permissions).
- `POST /api/v1/institutions`
  - Body: `{ display_name, institution_type_id, primary_contact_email, ... }`
  - Permission: Client Director or Platform Owner.
  - Action: Creates Institution and materializes `default_org_unit_template`.
- `PATCH /api/v1/institutions/{id}`
  - Body: `{ display_name, primary_contact_phone, ... }`
  - Permission: Client Director, Institution Admin, or Platform Owner.
- `GET /api/v1/institutions/{id}/org-units`
  - Query: `WITH RECURSIVE` CTE hierarchy list.
- `POST /api/v1/institutions/{id}/org-units`
  - Body: `{ name, type_id, parent_id, sort_order, code }`
  - Permission: Client Director or Institution Admin.
- `PATCH /api/v1/org-units/{id}/move`
  - Body: `{ new_parent_id }`
  - Permission: Client Director or Institution Admin.
  - Action: Validates cycle-prevention app-side, updates `parent_id`, emits `org_unit_moved` C-11 audit event.
- `POST /api/v1/org-units/{id}/archive`
  - Action: Soft-deletes node by setting `current_lifecycle_status` = `archived`.

### 3.2 Platform-Scoped Endpoints

- `POST /api/v1/platform/clients`
  - Body: `{ slug, display_name, legal_name, legal_entity_type_id, ... }`
  - Permission: Platform Owner.
- `POST /api/v1/platform/clients/{id}/lifecycle-transition`
  - Body: `{ target_status, reason }`
  - Permission: Platform Owner.
- `POST /api/v1/platform/institution-types`
  - Body: `{ name_id, code, default_org_unit_template }`
  - Permission: Platform Owner.
- `POST /api/v1/platform/ownership-transfers`
  - Body: `{ institution_id, from_client_id, to_client_id, reason }`
  - Permission: Platform Owner.

## 4. Key Implementation Rules & Validation

1. **Cycle Prevention Algorithm (Application Layer)**:
   ```python
   def check_cycle(repo, org_unit_id: UUID, new_parent_id: UUID):
       curr = new_parent_id
       while curr is not None:
           if curr == org_unit_id:
               raise CycleDetectedException("Cannot move an OrgUnit under its own descendant.")
           parent = repo.get_parent_id(curr)
           curr = parent
   ```
2. **Template Materialization**:
   - Recursively walks `default_org_unit_template` JSONB payload and inserts `org_unit` rows within a single DB transaction during institution creation.
3. **Single Transaction Ownership Transfer**:
   - Executes `UPDATE institution SET client_id = dest WHERE id = target`
   - Executes `UPDATE org_unit SET client_id = dest WHERE institution_id = target`
   - Updates downstream C-05 academic records, C-02 user assignments in the same transaction.
   - Writes `ownership_transfer_events` row.
   - Emits C-11 audit event (with historical events remaining tagged with original source `client_id`).
