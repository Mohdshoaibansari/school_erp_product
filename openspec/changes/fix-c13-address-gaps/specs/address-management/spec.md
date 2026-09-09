# Spec — Address Management (Gap Fixes)

> **Change:** fix-c13-address-gaps
> **Domain:** address-management
> **Impact:** MODIFIED (hardening G-01..G-19)
> **Base:** `openspec/changes/add-c13-address-management/specs/address-management/spec.md`
> **Source:** `docs/prd/C-13-Address-Management-PRD.md` §7/§24, `C-13-Address-Management-Gap-Register-and-Implementation-Plan.md` D1-D15

---

## MODIFIED Requirements

### Requirement: EntityType Entity

An `EntityType` SHALL be a controlled registry of entity types that may participate in C-13. The system SHALL resolve EntityType by immutable globally-unique `code` (not by random UUID), and SHALL expose centralized lookup via `EntityTypeRepo`/`EntityTypeService`.

**Fields:**
- `id` (UUID, PK)
- `code` (VARCHAR(100), UNIQUE, NOT NULL) — `INSTITUTION`, `PERSON`
- `name` (VARCHAR(255), NOT NULL) — Display name
- `created_at` (TIMESTAMPTZ)

**Rules:**
- EntityTypes are module-owned and registered through migration/seed; registration SHALL be deterministic and idempotent by `code`.
- `code` and `name` SHALL be immutable after creation.
- Application startup SHALL NOT create EntityTypes.
- Deletion SHALL be migration-only; once referenced by `AddressAssignment`, the EntityType SHALL be permanently protected.
- Routes and services SHALL resolve EntityType by stable `code` (`PERSON` for `person_addresses.py`, `INSTITUTION` for `institution_addresses.py`) via the centralized accessor; generation of random UUIDs for EntityType resolution SHALL be prohibited.
- Unregistered EntityType codes SHALL be rejected with `ENTITY_TYPE_NOT_FOUND`.

#### Scenario: Resolve EntityType by code for Person routes

- **WHEN** a client calls `POST /persons/{person_id}/addresses` with `PERSON` as the entity type
- **THEN** the system SHALL look up `entity_type` where `code = 'PERSON'` and use its persisted `id` for the `AddressAssignment`
- **AND** the same `id` SHALL be returned on every invocation (deterministic)

#### Scenario: Reject unregistered EntityType code

- **WHEN** a service resolves an EntityType by an unregistered code
- **THEN** the system SHALL reject with `ENTITY_TYPE_NOT_FOUND`

#### Scenario: No random UUID in EntityType resolution

- **WHEN** code is inspected for EntityType resolution paths
- **THEN** no `uuid4()` or random-UUID generation SHALL exist in those paths

#### Scenario: List EntityTypes

- **WHEN** user requests EntityTypes
- **THEN** system SHALL return all registered EntityTypes

---

### Requirement: AddressType Entity

An `AddressType` SHALL define the semantic purpose of an address. The system SHALL resolve AddressType by immutable globally-unique `code` (not random UUID) and SHALL filter compatibility strictly by the allow-list.

**Fields:**
- `id` (UUID, PK)
- `code` (VARCHAR(100), UNIQUE, NOT NULL) — `RESIDENTIAL`, `PERMANENT`, `CORRESPONDENCE`, `OFFICE`, `EMERGENCY`
- `name` (VARCHAR(255), NOT NULL) — Editable display name
- `created_at` (TIMESTAMPTZ)

**Rules:**
- AddressTypes are platform-managed, data-driven, not enums; `code` SHALL be immutable, `name` SHALL be editable.
- No active/inactive/retired lifecycle SHALL exist; deletable only if never used by any `AddressAssignment` (ever used = permanently protected).
- Compatibility SHALL be an explicit allow-list in `address_type_entity_type`; unconfigured compatibility SHALL be denied.
- Removing compatibility SHALL be blocked while assignments exist that depend on it.
- Services and routes SHALL resolve AddressType by stable `code` via centralized `AddressTypeRepo`/`AddressTypeService`; random-UUID generation for AddressType lookup SHALL be prohibited.
- `list_compatible_types(entity_type_code)` SHALL query the compatibility matrix for the EntityType resolved by `code` and SHALL return only AddressTypes whose `address_type_id` is in that compatible set (not all types).
- Creation of an `AddressAssignment` SHALL validate that the requested AddressType is compatible with the target EntityType; incompatible combinations SHALL be rejected with `ADDRESS_TYPE_NOT_COMPATIBLE`.
- Deleting an AddressType or removing a compatibility row SHALL be rejected while any `AddressAssignment` (including hard-deleted history conceptually "ever used") exists.

#### Scenario: Resolve AddressType by code

- **WHEN** a client creates an assignment with `address_type_code = 'RESIDENTIAL'` for `PERSON`
- **THEN** the system SHALL look up `address_type` where `code = 'RESIDENTIAL'` and use its persisted `id`

#### Scenario: Compatibility filtering returns only allowed types

- **WHEN** user requests compatible AddressTypes for `PERSON`
- **THEN** system SHALL return only `RESIDENTIAL`, `PERMANENT`, `CORRESPONDENCE`, `EMERGENCY` and SHALL NOT return `OFFICE`
- **WHEN** user requests compatible AddressTypes for `INSTITUTION`
- **THEN** system SHALL return only `OFFICE`, `CORRESPONDENCE`, `EMERGENCY`

#### Scenario: No compatibility returns empty

- **WHEN** no compatibility rows exist for a given EntityType
- **THEN** `list_compatible_types` SHALL return an empty list

#### Scenario: Reject incompatible assignment

- **WHEN** admin creates an `AddressAssignment` with `OFFICE` for `PERSON`
- **THEN** system SHALL reject with `ADDRESS_TYPE_NOT_COMPATIBLE`

#### Scenario: AddressType Deletion Protection

- **WHEN** admin attempts to delete an AddressType that was ever used
- **THEN** system SHALL reject the deletion

---

### Requirement: Address Entity

An `Address` SHALL contain the postal address data and SHALL enforce field-length, required-field, hierarchy, and whitespace-normalization invariants.

**Fields:**
- `id` (UUID, PK)
- `address_line_1` (VARCHAR(500), NOT NULL)
- `address_line_2` (VARCHAR(500), NULLABLE)
- `locality` (VARCHAR(100), NULLABLE)
- `landmark` (VARCHAR(100), NULLABLE)
- `postal_code` (VARCHAR(20), NOT NULL) — **Required** per 2026-09-07 grill amendment (D14/G-06); no country-specific validation in Phase 1
- `city_id` (UUID, FK → city.id, NOT NULL)
- `state_id` (UUID, FK → state.id, NOT NULL)
- `country_id` (UUID, FK → country.id, NOT NULL)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT now())
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT now(), onupdate now())

**Validation Rules:**
- `address_line_1` SHALL be required, max 500; `postal_code` SHALL be required, max 20; `city_id`/`state_id`/`country_id` SHALL be required.
- `address_line_2` max 500, `locality` max 100, `landmark` max 100; exceeding any max SHALL be rejected with `ADDRESS_OVERLY_LONG` (no silent truncation, DB constraints as second layer).
- All text fields SHALL have leading and trailing whitespace trimmed only; internal whitespace, capitalization and punctuation SHALL be preserved.
- For optional fields (`address_line_2`, `locality`, `landmark`): missing, `null`, or whitespace-only SHALL normalize to `NULL`; no empty-string/`NULL` dual representation.
- For required fields (`address_line_1`, `postal_code`): missing, `null`, or whitespace-only SHALL be rejected with `ADDRESS_REQUIRED_FIELD`; blank/whitespace `postal_code` SHALL never become `NULL`.
- Geographic hierarchy SHALL be valid on every write path (`create`, `update`, `correct`, `replace`): the resolved `City.state_id` SHALL equal `state_id` and `State.country_id` SHALL equal `country_id`; otherwise SHALL reject with `GEOGRAPHIC_HIERARCHY_INVALID`. Missing geo references SHALL also be rejected.

#### Scenario: Create Address with required postal_code

- **WHEN** admin creates an Address with valid `address_line_1`, `postal_code`, `city_id`, `state_id`, `country_id`
- **THEN** system SHALL trim whitespace, normalize empty optional values to `NULL`, validate hierarchy, and create the Address

#### Scenario: Reject whitespace-only postal_code

- **WHEN** admin creates an Address with `postal_code = "   "`
- **THEN** system SHALL reject with `ADDRESS_REQUIRED_FIELD` and SHALL NOT store `NULL`

#### Scenario: Normalize optional blank values

- **WHEN** admin creates an Address with `locality = "   "` and `landmark = "   "`
- **THEN** system SHALL normalize both to `NULL`

#### Scenario: Reject over-length input

- **WHEN** admin creates an Address with `address_line_1` exceeding 500 characters or `postal_code` exceeding 20
- **THEN** system SHALL reject with `ADDRESS_OVERLY_LONG`

#### Scenario: Trim whitespace

- **WHEN** admin submits `address_line_1 = "  MG Road  "`
- **THEN** system SHALL store `address_line_1 = "MG Road"`

#### Scenario: Validate geographic hierarchy

- **WHEN** admin creates an Address with `City` from State A but `state_id` = State B
- **THEN** system SHALL reject with `GEOGRAPHIC_HIERARCHY_INVALID`

---

### Requirement: Geographic Reference Data

Country, State, and City SHALL be normalized, hierarchical, migration-managed reference data and SHALL enforce code uniqueness and hierarchy.

**Country:**
- `id` (UUID, PK)
- `code` (VARCHAR(10), UNIQUE, NOT NULL) — `IN`, `US`, etc., globally unique, immutable
- `name` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMPTZ)

**State:**
- `id` (UUID, PK)
- `country_id` (UUID, FK → country.id, NOT NULL)
- `code` (VARCHAR(10), NOT NULL) — unique within Country, immutable
- `name` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMPTZ)
- `UNIQUE(country_id, code)`

**City:**
- `id` (UUID, PK)
- `state_id` (UUID, FK → state.id, NOT NULL)
- `code` (VARCHAR(10), NOT NULL) — unique within State, immutable
- `name` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMPTZ)
- `UNIQUE(state_id, code)`

**Rules:**
- Geographic data SHALL be seed/migration managed only; no runtime CRUD APIs SHALL exist.
- Codes SHALL be immutable; names MAY change through migration/seed.
- Geographic records MAY be hard-deleted through migration only when no dependent `Address` exists.
- City/State/Country on an `Address` SHALL belong to the same hierarchy (enforced via `Address` validation); locality remains free text.

#### Scenario: Hierarchy codes are scoped unique

- **WHEN** two States share the same `code` under different Countries
- **THEN** the system SHALL allow it; but two States with same `code` under the same Country SHALL be rejected by the UNIQUE constraint

#### Scenario: No runtime CRUD for geographic data

- **WHEN** a client attempts `POST /countries` or `DELETE /cities/{id}` at runtime
- **THEN** the system SHALL have no such endpoint and SHALL return 404/405

#### Scenario: List Countries / States / Cities

- **WHEN** user requests countries
- **THEN** system SHALL return all seeded countries
- **WHEN** user requests states for a country
- **THEN** system SHALL return only states belonging to that country
- **WHEN** user requests cities for a state
- **THEN** system SHALL return only cities belonging to that state

---

### Requirement: AddressAssignment Entity

An `AddressAssignment` SHALL associate an entity with an Address, AddressType, and validity period and SHALL enforce ownership exclusivity and temporal integrity at both application and database levels.

**Fields:**
- `id` (UUID, PK)
- `entity_type_id` (UUID, FK → entity_type.id, NOT NULL)
- `entity_id` (UUID, NOT NULL) — Polymorphic reference, validated at application level
- `address_id` (UUID, FK → address.id, NOT NULL, **UNIQUE**)
- `address_type_id` (UUID, FK → address_type.id, NOT NULL)
- `valid_from` (DATE, NOT NULL)
- `valid_to` (DATE, NULLABLE)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT now())
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT now(), onupdate now())

**Constraints:**
- `CHECK (valid_to IS NULL OR valid_to >= valid_from)`
- `UNIQUE(address_id)` SHALL enforce that an `Address` belongs to exactly one `AddressAssignment` and SHALL prevent reuse across entities
- `UNIQUE` or exclusion handling on `(entity_type_id, entity_id, address_type_id, valid_from)` as applicable for duplicate guard

**Rules:**
- An `Address` SHALL belong to exactly one entity; the same `address_id` SHALL NOT be assigned to two entities; concurrent duplicate assignments SHALL fail safely via the `UNIQUE(address_id)` constraint.
- `AddressType` SHALL be immutable on an existing assignment; changing type SHALL require ending/removing the old assignment and creating a new one.
- `valid_from` SHALL be mandatory; `valid_to` SHALL be optional (`NULL` = ongoing) and inclusive; `valid_to < valid_from` SHALL be rejected with `ADDRESS_ASSIGNMENT_DATE_INVALID`; `valid_from == valid_to` SHALL be valid (same-day assignment).
- No overlapping periods SHALL exist for the same `entity + AddressType`; overlapping or fully-contained periods SHALL be rejected with `ADDRESS_ASSIGNMENT_OVERLAP`; adjacent periods where one ends on day D and next starts on D+1 SHALL be allowed.
- At most one effective assignment SHALL exist for a given `entity + AddressType` at any point in time, where effective means `valid_from <= today AND (valid_to IS NULL OR today <= valid_to)`. Creation of a second effective assignment SHALL be rejected.
- Future-effective assignments (`today < valid_from`) and historical assignments (`valid_to IS NOT NULL AND today > valid_to`) SHALL be supported and remain queryable.
- Scope SHALL be derived from the target entity; no `client_id`/`institution_id` on the assignment table.

#### Scenario: Create AddressAssignment with valid dates

- **WHEN** admin creates an `AddressAssignment` with `valid_from = 2026-09-01`, `valid_to = NULL` and no overlap for same entity+AddressType
- **THEN** system SHALL validate entity exists, address type compatible, hierarchy valid, dates valid, and create the assignment

#### Scenario: Reject overlapping assignment

- **WHEN** admin creates an `AddressAssignment` that overlaps an existing assignment for same `entity + AddressType`
- **THEN** system SHALL reject with `ADDRESS_ASSIGNMENT_OVERLAP`

#### Scenario: Reject duplicate effective assignment

- **WHEN** an effective assignment already exists for `entity + AddressType` and admin creates another with `valid_from <= today <= valid_to`
- **THEN** system SHALL reject with `ADDRESS_ASSIGNMENT_OVERLAP`

#### Scenario: Allow adjacent periods

- **WHEN** existing assignment has `valid_to = 2026-08-31` and new assignment has `valid_from = 2026-09-01` for same entity+AddressType
- **THEN** system SHALL allow creation

#### Scenario: Prevent Address reuse

- **WHEN** admin attempts to assign the same `address_id` to a second entity
- **THEN** system SHALL reject via application check and the `UNIQUE(address_id)` constraint SHALL prevent persistence

#### Scenario: Reject invalid date range and allow same-day

- **WHEN** admin submits `valid_to < valid_from`
- **THEN** system SHALL reject with `ADDRESS_ASSIGNMENT_DATE_INVALID`
- **WHEN** admin submits `valid_from == valid_to`
- **THEN** system SHALL allow it

---

### Requirement: Address Replacement

When an entity actually moves, the system SHALL support atomic address replacement (end old, create new Address, create new assignment) as a single transaction.

**Rules:**
- The operation SHALL: 1) end the old assignment by setting `valid_to`, 2) create a new `Address` row (never reuse), 3) create a new `AddressAssignment`; all three SHALL be in one transaction and SHALL roll back entirely if any step fails.
- The old `Address` SHALL remain intact for historical records.
- Hierarchy, field validation, compatibility, and temporal overlap rules SHALL be re-validated for the new Address/Assignment.
- If an entity later returns to the same postal location, the system SHALL create a new `Address` record (no reuse).

#### Scenario: Replace Address atomically

- **WHEN** admin replaces an address for `entity + AddressType` with valid new address data
- **THEN** system SHALL end the old assignment, create a new Address, create a new assignment in one transaction

#### Scenario: Rollback on replacement failure

- **WHEN** replacement fails during creation of the new Address (e.g., hierarchy invalid)
- **THEN** system SHALL roll back the `valid_to` update on the old assignment and SHALL persist no partial state

#### Scenario: Old Address remains historical

- **WHEN** replacement succeeds
- **THEN** the old Address row SHALL still exist and be queryable via historical assignments

---

### Requirement: Address Deletion

Deleting an `AddressAssignment` SHALL delete its owned `Address` atomically; no orphan `Address` records SHALL remain and no independent business-level Address delete bypassing assignment ownership SHALL exist.

**Rules:**
- Deletion SHALL be invoked via the assignment ownership (e.g., `DELETE /addresses/{address_id}` resolved to its `AddressAssignment`).
- The system SHALL delete the `AddressAssignment` and its owned `Address` in the same transaction; if either fails the whole operation SHALL roll back.
- An `Address` SHALL NOT be independently deletable while still assigned; orphan `Address` records SHALL be prohibited.
- Missing or already-deleted resources SHALL be handled consistently (idempotent 404).

#### Scenario: Delete assignment and owned Address atomically

- **WHEN** admin deletes an `AddressAssignment` with `address.delete` permission
- **THEN** system SHALL delete the assignment and its owned Address in the same transaction and no orphan SHALL remain

#### Scenario: Rollback on deletion failure

- **WHEN** deletion fails after removing the assignment but before removing the Address
- **THEN** system SHALL roll back and both rows SHALL remain

#### Scenario: No orphan Address after deletion

- **WHEN** all assignments are listed after a successful deletion
- **THEN** no `Address` row SHALL exist without a corresponding `AddressAssignment` for the deleted entity

---

### Requirement: Address Correction

Effective addresses SHALL be mutable only through a controlled correction operation with dedicated authorization; ordinary update SHALL NOT bypass correction.

**Rules:**
- Ordinary `PATCH /addresses/{id}` SHALL only allow mutation when the address is **future** (`today < valid_from`); attempts to patch an **effective** (`valid_from <= today <= valid_to/null`) address via ordinary update SHALL be rejected and the client SHALL be directed to the correction endpoint; **historical** (`valid_to < today`) addresses SHALL be immutable via ordinary update.
- Correction SHALL be via `POST /addresses/{id}/correct` and SHALL require `address.correct` permission (separate from `address.update`).
- Correction SHALL be allowed only when the target `Address` is currently **effective**; correcting a future or historical address SHALL be rejected.
- Correction SHALL mutate the `Address` in place (controlled fix, e.g., `Banglore → Bangalore`) transactionally, SHALL capture before/after values, SHALL emit an audit event via `AuditEmitter`, and SHALL update `updated_at`.
- Date editing on an effective assignment MAY be performed via assignment date update subject to temporal invariants; type change SHALL still require replacement.

#### Scenario: Ordinary update allowed only for future address

- **WHEN** admin PATCHes a future Address (`today < valid_from`) with valid fields
- **THEN** system SHALL allow the update
- **WHEN** admin PATCHes an effective Address via ordinary `PATCH`
- **THEN** system SHALL reject and indicate correction is required

#### Scenario: Reject ordinary update of historical address

- **WHEN** admin PATCHes a historical Address (`valid_to < today`)
- **THEN** system SHALL reject

#### Scenario: Correct effective Address with permission

- **WHEN** admin with `address.correct` posts correction for an effective Address
- **THEN** system SHALL apply the correction transactionally

#### Scenario: Reject correction without permission or for non-effective address

- **WHEN** user without `address.correct` attempts correction
- **THEN** system SHALL reject with authorization error
- **WHEN** admin attempts correction for a future or historical Address
- **THEN** system SHALL reject with validation error

---

### Requirement: Tenant Boundaries

C-13 SHALL respect the platform tenancy model and SHALL NOT duplicate scope columns.

**Rules:**
- `Address` and `AddressAssignment` SHALL NOT store `client_id` or `institution_id`; scope SHALL be derived from the target entity (`Person` → `institution_id`, `Institution` → `client_id`).
- Every addressable entity SHALL be scoped; C-13 SHALL NOT support unscoped/platform-level addressable entities.
- C-13 SHALL use existing C-04/Casbin application-level authorization as the sole decision-maker; polymorphic association SHALL NOT bypass authorization or tenant isolation.
- Requests SHALL: resolve target entity, resolve authoritative scope facts, build/augment `ResourceContext`, delegate to C-04/Casbin, and execute only when authorized.

#### Scenario: Entity scope derivation

- **WHEN** user requests addresses for an entity
- **THEN** system SHALL resolve the entity's scope and enforce authorization via C-04 before returning data

#### Scenario: Cross-scope access denied

- **WHEN** user scoped to Institution A requests addresses for an entity in Institution B and policy denies
- **THEN** system SHALL deny access

---

### Requirement: Audit Integration

Address mutations SHALL integrate with the platform audit capability via the existing `AuditEmitter` interface; no parallel audit mechanism SHALL be created.

**Events:**
- `address.created`
- `address.updated` (future-only ordinary update)
- `address.deleted` (assignment + owned address)
- `address.corrected` (with before/after)
- `address.assignment_created`
- `address.assignment_ended` (replacement)

**Rules:**
- Every mutation SHALL emit the corresponding event transactionally where required: `address.corrected` SHALL include `before` and `after` values where the audit framework supports it.
- `address.corrected` SHALL include `who`, `when`, and field-level diff; unauthorized correction SHALL emit no mutation event.
- Correction audit and business write SHALL be atomic; failure to emit where transactional SHALL roll back the correction.
- Hard deletion as a destructive operation SHALL be auditable via `address.deleted`.

#### Scenario: Emit audit on address creation

- **WHEN** an Address + Assignment is created
- **THEN** system SHALL emit `address.created` and `address.assignment_created` via `AuditEmitter`

#### Scenario: Emit correction audit with before/after

- **WHEN** an effective Address is corrected with `address.correct`
- **THEN** system SHALL emit `address.corrected` with `before` and `after` payloads and the actor identity

#### Scenario: No audit on rejected correction

- **WHEN** correction is rejected (not effective or unauthorized)
- **THEN** system SHALL NOT emit a mutation audit event

