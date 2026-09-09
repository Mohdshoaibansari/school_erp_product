# Spec — Address Management

> **Change:** add-c13-address-management
> **Domain:** address-management
> **Impact:** ADDED (new domain)
> **Source:** `docs/prd/C-13-Address-Management-PRD.md`, `docs/prd/c-13-impact-classification.md`

---

## ADDED Requirements

### Requirement: EntityType Entity

An `EntityType` SHALL be a controlled registry of entity types that may participate in C-13.

**Fields:**
- `id` (UUID, PK)
- `code` (VARCHAR(100), UNIQUE, NOT NULL) — 'INSTITUTION', 'PERSON'
- `name` (VARCHAR(255), NOT NULL) — Display name
- `created_at` (TIMESTAMPTZ)

**Rules:**
- EntityTypes are module-owned and registered through migration/seed
- Code and name are immutable after creation
- Application startup must not create EntityTypes
- Deletion is migration-only
- Once referenced by AddressAssignment, permanently protected

#### Scenario: List EntityTypes

- **WHEN** user requests EntityTypes
- **THEN** system SHALL return all registered EntityTypes

#### Scenario: EntityType Registration

- **WHEN** a module is migrated
- **THEN** its EntityType SHALL be registered idempotently

---

### Requirement: AddressType Entity

An `AddressType` SHALL define the semantic purpose of an address.

**Fields:**
- `id` (UUID, PK)
- `code` (VARCHAR(100), UNIQUE, NOT NULL) — 'RESIDENTIAL', 'PERMANENT', etc.
- `name` (VARCHAR(255), NOT NULL) — Editable display name
- `created_at` (TIMESTAMPTZ)

**Rules:**
- AddressTypes are platform-managed, data-driven, not enums
- Code is immutable; name is editable
- No active/inactive/retired lifecycle
- Deletable only if never used by any AddressAssignment (ever used = permanently protected)
- Compatibility is explicit allow-list
- Removing compatibility is blocked while assignments exist

#### Scenario: List AddressTypes

- **WHEN** user requests AddressTypes
- **THEN** system SHALL return all platform-managed AddressTypes

#### Scenario: List Compatible AddressTypes

- **WHEN** user requests compatible AddressTypes for an EntityType
- **THEN** system SHALL return only the allowed AddressTypes

#### Scenario: AddressType Deletion Protection

- **WHEN** admin attempts to delete an AddressType that was ever used
- **THEN** system SHALL reject the deletion

---

### Requirement: Address Entity

An `Address` SHALL contain the postal address data.

**Fields:**
- `id` (UUID, PK)
- `address_line_1` (VARCHAR(500), NOT NULL) — Primary address line
- `address_line_2` (VARCHAR(500), NULLABLE) — Additional details
- `locality` (VARCHAR(100), NULLABLE) — Free text
- `landmark` (VARCHAR(100), NULLABLE) — Free text
- `postal_code` (VARCHAR(20), NULLABLE) — No country-specific validation in Phase 1
- `city_id` (UUID, FK → city.id, NOT NULL)
- `state_id` (UUID, FK → state.id, NOT NULL)
- `country_id` (UUID, FK → country.id, NOT NULL)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Validation Rules:**
- All text fields: trim leading/trailing whitespace
- Optional blank values normalize to NULL
- Missing/null/whitespace optional values normalize to NULL
- Application rejects over-length input (no silent truncation)
- Geographic hierarchy must be valid (City belongs to State belongs to Country)

#### Scenario: Create Address

- **WHEN** admin creates an Address with valid data
- **THEN** system SHALL trim whitespace, normalize empty values, and create the Address

#### Scenario: Reject Over-Length Input

- **WHEN** admin creates an Address with address_line_1 exceeding 500 characters
- **THEN** system SHALL reject with validation error

#### Scenario: Normalize Optional Blank Values

- **WHEN** admin creates an Address with locality = "   "
- **THEN** system SHALL normalize locality to NULL

#### Scenario: Validate Geographic Hierarchy

- **WHEN** admin creates an Address with City from State A but State from State B
- **THEN** system SHALL reject with validation error

---

### Requirement: AddressAssignment Entity

An `AddressAssignment` SHALL associate an entity with an Address, AddressType, and validity period.

**Fields:**
- `id` (UUID, PK)
- `entity_type_id` (UUID, FK → entity_type.id, NOT NULL)
- `entity_id` (UUID, NOT NULL) — Polymorphic reference
- `address_id` (UUID, FK → address.id, NOT NULL)
- `address_type_id` (UUID, FK → address_type.id, NOT NULL)
- `valid_from` (DATE, NOT NULL)
- `valid_to` (DATE, NULLABLE)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Constraints:**
- `valid_to IS NULL OR valid_to >= valid_from` (CHECK)

**Rules:**
- Address belongs to exactly one entity
- AddressType cannot be changed on existing assignment (type change = new assignment)
- One effective assignment per entity + AddressType
- No overlapping periods for same entity + AddressType
- `valid_from` is mandatory
- `valid_to` is optional (NULL = ongoing)
- `valid_to` is inclusive
- Future-effective assignments supported
- Historical assignments preserved
- Scope derived from target entity (no client_id/institution_id on assignment)

#### Scenario: Create Address Assignment

- **WHEN** admin creates an AddressAssignment with valid data
- **THEN** system SHALL validate entity exists, address type is compatible, no overlap, and dates are valid
- **AND** system SHALL create the assignment

#### Scenario: Reject Incompatible AddressType

- **WHEN** admin creates an AddressAssignment with AddressType not compatible with EntityType
- **THEN** system SHALL reject with validation error

#### Scenario: Reject Overlapping Assignment

- **WHEN** admin creates an AddressAssignment that overlaps with existing assignment for same entity + AddressType
- **THEN** system SHALL reject with validation error

#### Scenario: Reject Invalid Date Range

- **WHEN** admin creates an AddressAssignment with valid_to < valid_from
- **THEN** system SHALL reject with validation error

---

### Requirement: Address Replacement

When an entity moves, the system SHALL support atomic address replacement.

#### Scenario: Replace Address

- **WHEN** admin replaces an address
- **THEN** system SHALL end the old assignment (set valid_to)
- AND create a new Address record
- AND create a new AddressAssignment
- AND all SHALL be in a single transaction

---

### Requirement: Address Correction

Effective addresses MAY be corrected through a controlled operation. The correction SHALL have separate authorization (`address.correct`).

#### Scenario: Correct Effective Address

- **WHEN** admin corrects an effective Address with `address.correct` permission
- **THEN** system SHALL apply the correction
- AND emit an audit event with before/after values

#### Scenario: Reject Unauthorized Correction

- **WHEN** user without `address.correct` permission attempts to correct an effective Address
- **THEN** system SHALL reject with authorization error

---

### Requirement: Address Deletion

Deleting an AddressAssignment SHALL delete its owned Address.

#### Scenario: Delete Address Assignment

- **WHEN** admin deletes an AddressAssignment
- **THEN** system SHALL delete the assignment
- AND delete the owned Address in the same transaction
- AND no orphan Address records SHALL remain

---

### Requirement: Geographic Reference Data

Country, State, and City SHALL be normalized reference data.

**Country:**
- `id` (UUID, PK)
- `code` (VARCHAR(10), UNIQUE, NOT NULL) — 'IN', 'US', etc.
- `name` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMPTZ)

**State:**
- `id` (UUID, PK)
- `country_id` (UUID, FK → country.id, NOT NULL)
- `code` (VARCHAR(10), NOT NULL) — Unique within country
- `name` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMPTZ)

**City:**
- `id` (UUID, PK)
- `state_id` (UUID, FK → state.id, NOT NULL)
- `code` (VARCHAR(10), NOT NULL) — Unique within state
- `name` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMPTZ)

**Rules:**
- Geographic data is seed/migration managed only
- No runtime CRUD APIs for geographic records
- Codes are immutable
- Names may change through migration/seed
- Geographic records may be deleted through migration when unused
- City/State/Country must belong to the same hierarchy

#### Scenario: List Countries

- **WHEN** user requests countries
- **THEN** system SHALL return all countries

#### Scenario: List States for Country

- **WHEN** user requests states for a country
- **THEN** system SHALL return states belonging to that country

#### Scenario: List Cities for State

- **WHEN** user requests cities for a state
- **THEN** system SHALL return cities belonging to that state

---

### Requirement: Tenant Boundaries

C-13 SHALL respect the platform tenancy model.

**Rules:**
- Address and AddressAssignment do NOT store client_id or institution_id
- Scope is derived from the target entity
- C-13 uses existing C-04 authorization
- Polymorphic association cannot bypass authorization or tenant isolation

#### Scenario: Entity Scope Derivation

- **WHEN** user requests addresses for an entity
- **THEN** system SHALL resolve the entity's scope and enforce authorization

---

### Requirement: Audit Integration

Address mutations SHALL integrate with the platform audit capability.

**Events:**
- `address.created`
- `address.updated`
- `address.deleted`
- `address.corrected`
- `address.assignment_created`
- `address.assignment_ended`

#### Scenario: Emit Audit on Address Creation

- **WHEN** an Address is created
- **THEN** system SHALL emit `address.created` audit event

#### Scenario: Emit Audit on Address Correction

- **WHEN** an Address is corrected
- **THEN** system SHALL emit `address.corrected` audit event with before/after values

---

## Seeded Data

### EntityTypes

| Code | Name |
|---|---|
| `INSTITUTION` | Institution |
| `PERSON` | Person |

### AddressTypes

| Code | Name |
|---|---|
| `RESIDENTIAL` | Residential |
| `PERMANENT` | Permanent |
| `CORRESPONDENCE` | Correspondence |
| `OFFICE` | Office |
| `EMERGENCY` | Emergency |

### Compatibility Matrix

| EntityType | Allowed AddressTypes |
|---|---|
| `PERSON` | RESIDENTIAL, PERMANENT, CORRESPONDENCE, EMERGENCY |
| `INSTITUTION` | OFFICE, CORRESPONDENCE, EMERGENCY |

---

## API Endpoints

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

## Error Codes

| Code | Description |
|---|---|
| `ENTITY_TYPE_NOT_FOUND` | EntityType not registered |
| `ADDRESS_TYPE_NOT_FOUND` | AddressType does not exist |
| `ADDRESS_TYPE_NOT_COMPATIBLE` | AddressType not compatible with EntityType |
| `ADDRESS_OVERLY_LONG` | Address field exceeds maximum length |
| `ADDRESS_REQUIRED_FIELD` | Required field is missing or empty |
| `GEOGRAPHIC_HIERARCHY_INVALID` | City/State/Country hierarchy is invalid |
| `ADDRESS_ASSIGNMENT_OVERLAP` | Overlapping assignment for entity + address type |
| `ADDRESS_ASSIGNMENT_DATE_INVALID` | Invalid date range |
| `ADDRESS_NOT_FOUND` | Address does not exist |
| `ADDRESS_ASSIGNMENT_NOT_FOUND` | AddressAssignment does not exist |
| `ADDRESS_IN_USE` | AddressType is in use and cannot be deleted |
