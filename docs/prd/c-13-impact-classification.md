# Impact Classification — C-13 Address Management

> **Capability:** C-13 Address Management
> **Status:** Draft
> **Last updated:** 2026-09-05
> **Source:** `docs/prd/C-13-Address-Management-PRD.md`, grill session 2026-09-05

---

## 1. Impact Summary

C-13 is a **new kernel capability** that provides a centralized, reusable Address Management capability for the School ERP. It supports addresses belonging to ERP entities (Person, Institution) with temporal assignments, geographic reference data, and address type compatibility. This is a greenfield implementation — no production data to preserve.

| Impact Type | Count |
|---|---|
| **ADDED** (new tables) | 7 new tables |
| **MODIFIED** (existing tables) | 0 tables modified |
| **REMOVED** (deprecated tables) | 0 tables removed |
| **CROSS-CUTTING** (multiple domains) | 3 capabilities affected |

---

## 2. Key Design Decisions (from Grill Session)

| # | Decision | Rationale |
|---|---|---|
| D1 | Module at `kernel/address/` (singular) | Matches existing conventions |
| D2 | Only 2 EntityTypes: INSTITUTION, PERSON | Student/Employee/Staff all reference Person |
| D3 | Generic polymorphic `entity_type_id` + `entity_id` | Flexible, simple, aligns with PRD |
| D4 | No `client_id`/`institution_id` on Address tables | Scope derived from target entity |
| D5 | C-04 app-level authorization (no RLS initially) | Consistency with existing pattern |
| D6 | Seed India geographic data initially | Manageable dataset, expand later |
| D7 | App-level temporal overlap validation | Simpler than DB constraints |
| D8 | Hard delete Address with Assignment | No reuse, no orphans |
| D9 | Single transactional replace operation | Atomic business change |
| D10 | Separate correction endpoint with own permission | Controlled modification of effective data |
| D11 | Composite unique codes (country, state+country, city+state) | Hierarchical uniqueness |
| D12 | Integrate with existing AuditEmitter | Consistent with platform |
| D13 | Entity-specific routes in `kernel/address/` | Simpler for Phase 1 |

---

## 3. Table Changes

### 3.1 Tables to CREATE (7)

#### `entity_type`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `code` | VARCHAR(100) | UNIQUE, NOT NULL | 'INSTITUTION', 'PERSON' |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Rules:**
- Code and name are immutable after creation
- Deletion is migration-only
- Once referenced by AddressAssignment, permanently protected

#### `address_type`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `code` | VARCHAR(100) | UNIQUE, NOT NULL | 'RESIDENTIAL', 'PERMANENT', etc. |
| `name` | VARCHAR(255) | NOT NULL | Editable display name |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Rules:**
- Code is immutable, name is editable
- No active/inactive lifecycle
- Deletable only if never used by any AddressAssignment

#### `address_type_entity_type` (compatibility matrix)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `address_type_id` | UUID | FK → address_type.id, PK | |
| `entity_type_id` | UUID | FK → entity_type.id, PK | |

**Rules:**
- Explicit allow-list compatibility
- Unconfigured compatibility = denied
- Removing compatibility blocked while assignments exist

#### `address`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `address_line_1` | VARCHAR(500) | NOT NULL | Primary address line |
| `address_line_2` | VARCHAR(500) | NULLABLE | Additional details |
| `locality` | VARCHAR(100) | NULLABLE | Free text |
| `landmark` | VARCHAR(100) | NULLABLE | Free text |
| `postal_code` | VARCHAR(20) | NULLABLE | No country-specific validation |
| `city_id` | UUID | FK → city.id, NOT NULL | Normalized reference |
| `state_id` | UUID | FK → state.id, NOT NULL | Normalized reference |
| `country_id` | UUID | FK → country.id, NOT NULL | Normalized reference |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Rules:**
- No `client_id` or `institution_id` (scope derived from entity)
- All text fields: trim leading/trailing whitespace
- Optional blank values normalize to NULL

#### `address_assignment`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `entity_type_id` | UUID | FK → entity_type.id, NOT NULL | |
| `entity_id` | UUID | NOT NULL | Polymorphic (no FK) |
| `address_id` | UUID | FK → address.id, NOT NULL | |
| `address_type_id` | UUID | FK → address_type.id, NOT NULL | |
| `valid_from` | DATE | NOT NULL | |
| `valid_to` | DATE | NULLABLE | NULL = ongoing |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraints:**
- `valid_to IS NULL OR valid_to >= valid_to` (CHECK)

**Rules:**
- No `client_id` or `institution_id`
- AddressType immutable on assignment (change = new assignment)
- One effective assignment per entity + AddressType
- No overlapping periods for same entity + AddressType

#### `country`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `code` | VARCHAR(10) | UNIQUE, NOT NULL | 'IN', 'US', etc. |
| `name` | VARCHAR(255) | NOT NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

#### `state`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `country_id` | UUID | FK → country.id, NOT NULL | |
| `code` | VARCHAR(10) | NOT NULL | Unique within country |
| `name` | VARCHAR(255) | NOT NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraints:**
- UNIQUE(`country_id`, `code`)

#### `city`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `state_id` | FK → state.id, NOT NULL | |
| `code` | VARCHAR(10) | NOT NULL | Unique within state |
| `name` | VARCHAR(255) | NOT NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Constraints:**
- UNIQUE(`state_id`, `code`)

---

## 4. Entity Relationship Summary

```
EntityType ←── AddressTypeEntityType (compatibility)
                  │
                  ▼
EntityType ←── AddressAssignment ──→ Address
                  │                    │
                  │                    ├──→ City
                  │                    ├──→ State
                  │                    └──→ Country
                  │
                  └──→ AddressType
```

---

## 5. Business Invariants

| # | Invariant | Enforcement |
|---|---|---|
| 1 | Address belongs to exactly one entity | Application level |
| 2 | EntityType must be registered | DB FK |
| 3 | AddressType must exist | DB FK |
| 4 | AddressType/EntityType compatibility explicit | Application level |
| 5 | City/State/Country hierarchy valid | Application level |
| 6 | `valid_from <= valid_to` | DB CHECK |
| 7 | No overlapping periods for entity + AddressType | Application level |
| 8 | One effective assignment per entity + AddressType | Application level |
| 9 | Address deletion deletes owned Address | Application level (transaction) |
| 10 | Target entity scope is authoritative | Application level |
| 11 | Polymorphic association cannot bypass scope | Application level |
| 12 | Address records cannot be reused | Application level |
| 13 | AddressType immutable on assignment | Application level |

---

## 6. New Permissions (C-04)

| Permission | Description | Default Roles |
|---|---|---|
| `address.create` | Create address assignment | Admin, institution_admin |
| `address.read` | Read addresses | All roles |
| `address.update` | Update future address | Admin, institution_admin |
| `address.delete` | Delete address assignment + address | Admin, institution_admin |
| `address.correct` | Correct effective address | Admin, institution_admin |
| `address_type.read` | Read address types | All roles |
| `address_type.manage` | Manage address types | Platform admin |
| `entity_type.read` | Read entity types | All roles |

---

## 7. RLS Policies

No RLS in Phase 1. C-04 application-level authorization is used. RLS may be added later.

---

## 8. Cross-Cutting Impacts

### 8.1 Identity & User (C-02)

| Impact | Details |
|---|---|
| References Person | `entity_id` references `person.id` for PERSON type |
| No schema changes | C-02 tables unchanged |

### 8.2 Tenant & Institution (C-01)

| Impact | Details |
|---|---|
| References Institution | `entity_id` references `institution.id` for INSTITUTION type |
| No schema changes | C-01 tables unchanged |

### 8.3 Authorization (C-04)

| Impact | Details |
|---|---|
| New permissions | 8 new permissions for address management |
| Role assignments | Admin and institution_admin get address permissions |
| Casbin policies | New policies for address entities |

### 8.4 Audit (C-11)

| Impact | Details |
|---|---|
| AuditEmitter integration | Emit events for all address mutations |
| Events | address.created, updated, deleted, corrected, assignment_created, assignment_ended |

---

## 9. Seeded Data

### 9.1 EntityTypes

| Code | Name |
|---|---|
| `INSTITUTION` | Institution |
| `PERSON` | Person |

### 9.2 AddressTypes

| Code | Name |
|---|---|
| `RESIDENTIAL` | Residential |
| `PERMANENT` | Permanent |
| `CORRESPONDENCE` | Correspondence |
| `OFFICE` | Office |
| `EMERGENCY` | Emergency |

### 9.3 Compatibility Matrix

| EntityType | Allowed AddressTypes |
|---|---|
| `PERSON` | RESIDENTIAL, PERMANENT, CORRESPONDENCE, EMERGENCY |
| `INSTITUTION` | OFFICE, CORRESPONDENCE, EMERGENCY |

### 9.4 Geographic Data (India)

- 1 Country: India (IN)
- ~28 States
- ~500+ Cities (major cities per state)

---

## 10. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/persons/{person_id}/addresses` | List addresses for person |
| POST | `/api/v1/persons/{person_id}/addresses` | Create address assignment for person |
| GET | `/api/v1/institutions/{institution_id}/addresses` | List addresses for institution |
| POST | `/api/v1/institutions/{institution_id}/addresses` | Create address assignment for institution |
| GET | `/api/v1/addresses/{address_id}` | Get address details |
| PATCH | `/api/v1/addresses/{address_id}` | Update future address |
| DELETE | `/api/v1/addresses/{address_id}` | Delete address assignment + address |
| POST | `/api/v1/addresses/{address_id}/correct` | Correct effective address |
| POST | `/api/v1/addresses/{address_id}/replace` | Replace address (end old, create new) |
| GET | `/api/v1/address-types` | List address types |
| GET | `/api/v1/address-types/compatible` | List compatible address types for entity type |
| GET | `/api/v1/countries` | List countries |
| GET | `/api/v1/countries/{country_id}/states` | List states for country |
| GET | `/api/v1/states/{state_id}/cities` | List cities for state |

---

## 11. Service Layer

### AddressService

- `create_address()` — Create address + assignment (transactional)
- `get_address()` — Get address by ID
- `update_address()` — Update future address fields
- `delete_address()` — Delete assignment + address (transactional)
- `correct_address()` — Correct effective address (separate permission)
- `replace_address()` — End old assignment, create new address + assignment (transactional)

### AddressAssignmentService

- `create_assignment()` — Create assignment with validation
- `end_assignment()` — End assignment (set valid_to)
- `list_by_entity()` — List assignments for entity
- `list_effective()` — List effective assignments

### AddressTypeService

- `list_types()` — List all address types
- `list_compatible_types()` — List types compatible with entity type

### GeographicService

- `list_countries()` — List countries
- `list_states()` — List states for country
- `list_cities()` — List cities for state
- `validate_hierarchy()` — Validate city/state/country hierarchy

---

## 12. Migration Plan

### 12.1 Alembic Migration (027)

1. Create C-13 tables (7 tables: entity_type, address_type, address_type_entity_type, address, address_assignment, country, state, city)
2. Seed EntityTypes (INSTITUTION, PERSON)
3. Seed AddressTypes (RESIDENTIAL, PERMANENT, CORRESPONDENCE, OFFICE, EMERGENCY)
4. Seed compatibility matrix
5. Seed geographic data (India)
6. Seed permissions in `permission` and `role_permission`

### 12.2 Rollback Plan

- C-13 tables are new — drop on rollback
- Permissions soft-deleted on rollback

---

## 13. Testing Strategy

| Test Type | Scope |
|---|---|
| Unit tests | Address CRUD, validation, normalization |
| Unit tests | Geographic hierarchy validation |
| Unit tests | AddressType compatibility |
| Unit tests | Temporal overlap prevention |
| Unit tests | Address replacement (transactional) |
| Unit tests | Address correction |
| Integration tests | API/service/database interaction |
| Integration tests | Authorization (C-04) |
| Integration tests | Audit emission |

---

## 14. Effort Estimate

| Component | Estimate |
|---|---|
| C-13 models + repos | 2 days |
| C-13 services (address, assignment, type, geographic) | 3 days |
| C-13 routes + DTOs | 2 days |
| C-13 permissions | 0.5 day |
| Geographic data seeding | 1 day |
| Tests | 2 days |
| Documentation + verification | 0.5 day |
| **Total** | **~11 days** |

---

## 15. Deferred Items

The following are explicitly out of scope for Phase 1:

| Item | Reason |
|---|---|
| Latitude/longitude/GPS | Geospatial capability, not address |
| Geocoding/reverse geocoding | External service integration |
| Maps/distance calculations | Geospatial capability |
| Geographic zones | Future enhancement |
| Physical Location entity | Future enhancement |
| Pickup/drop-point management | Future enhancement |
| Institution-specific AddressType customization | Phase 2 |
| RLS implementation | Can be added later |
| Pagination/filtering | Can be added later |
| API idempotency | Can be added later |

---

## 16. Module Integration

C-13 is the single source of truth for address data. The following modules will consume C-13:

| Module | Usage |
|---|---|
| C-01 Institution | Institution addresses |
| C-02 Person | Person addresses |
| Future Student | Student addresses (via Person) |
| Future Employee | Employee addresses (via Person) |
| Fees | Billing address resolution |
| Communication | Mailing address resolution |
| Transport | Pickup/drop address resolution |

**No consumer module may maintain a duplicate address table for the same business fact.**
