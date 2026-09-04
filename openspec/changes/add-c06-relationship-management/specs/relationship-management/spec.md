# Spec — Relationship Management Framework

> **Change:** add-c06-relationship-management
> **Domain:** relationship-management
> **Impact:** ADDED (new domain)
> **Source:** `docs/prd/C-06-Relationship-Management-Framework-PRD.md`, `docs/prd/c-06-impact-classification.md`

---

## ADDED Requirements

### Requirement: RelationshipType Entity

A `RelationshipType` SHALL define the semantic classification of a Relationship between two Persons.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `code` (VARCHAR(100), UNIQUE, NOT NULL)
- `name` (VARCHAR(255), NOT NULL)
- `inverse_relationship_type_id` (UUID, FK → relationship_type.id, NULLABLE)
- `is_symmetric` (BOOLEAN, NOT NULL, DEFAULT false)
- `created_at` (TIMESTAMPTZ)

**Rules:**
- RelationshipTypes SHALL be data-driven, not hard-coded enums
- RelationshipTypes SHALL be platform-managed globally
- Semantic definition (code, name, inverse, is_symmetric) SHALL be immutable after creation
- Non-symmetric RelationshipType MUST have an inverse
- Inverse pair SHALL be created transactionally (auto-generated)
- Symmetric types SHALL have `is_symmetric = true` and `inverse_relationship_type_id = NULL`

#### Scenario: Create Non-Symmetric RelationshipType

- **WHEN** admin creates a RelationshipType with `is_symmetric = false`
- **THEN** system SHALL auto-generate the inverse RelationshipType
- **AND** both types SHALL be linked to each other via `inverse_relationship_type_id`
- **AND** creation SHALL be transactional (both succeed or both fail)

#### Scenario: Create Symmetric RelationshipType

- **WHEN** admin creates a RelationshipType with `is_symmetric = true`
- **THEN** system SHALL create only one RelationshipType
- **AND** `inverse_relationship_type_id` SHALL be NULL

#### Scenario: Immutability Enforcement

- **WHEN** admin attempts to update RelationshipType semantic fields
- **THEN** system SHALL reject the request

---

### Requirement: ContactRole Entity

A `ContactRole` SHALL represent a responsibility attached to a specific Relationship.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `code` (VARCHAR(100), UNIQUE, NOT NULL)
- `name` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMPTZ)

**Rules:**
- ContactRoles SHALL be platform-managed entities, not hard-coded enums
- ContactRole SHALL be Relationship-specific (not a global Person property)
- A Relationship MAY have zero or more ContactRoleAssignments
- Multiple different ContactRoles MAY be effective simultaneously
- There is no cross-role exclusivity

#### Scenario: List ContactRoles

- **WHEN** user requests ContactRoles
- **THEN** system SHALL return all platform-managed ContactRoles

---

### Requirement: RelationshipType-ContactRole Compatibility

The platform SHALL define which ContactRoles are valid for each RelationshipType using an explicit allow-list.

**Table:** `relationship_type_contact_role`
- `relationship_type_id` (UUID, FK → relationship_type.id)
- `contact_role_id` (UUID, FK → contact_role.id)
- UNIQUE(`relationship_type_id`, `contact_role_id`)

**Rules:**
- If a role is not explicitly allowed, it SHALL be denied by default
- Compatibility is an explicit allow-list

#### Scenario: Validate ContactRole Compatibility

- **WHEN** admin assigns a ContactRole to a Relationship
- **THEN** system SHALL validate the ContactRole is compatible with the Relationship's RelationshipType
- **AND** if not compatible, system SHALL reject with `CONTACT_ROLE_NOT_ALLOWED` error

#### Scenario: List Compatible Roles

- **WHEN** user requests compatible ContactRoles for a RelationshipType
- **THEN** system SHALL return only the allowed ContactRoles

---

### Requirement: Relationship Entity

A `Relationship` SHALL connect exactly two different Persons with temporal validity.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `person_a_id` (UUID, FK → person.id, NOT NULL)
- `person_b_id` (UUID, FK → person.id, NOT NULL)
- `relationship_type_id` (UUID, FK → relationship_type.id, NOT NULL)
- `valid_from` (DATE, NOT NULL)
- `valid_to` (DATE, NULLABLE)
- `normalized_pair` (VARCHAR(255), UNIQUE, NOT NULL)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Constraints:**
- `person_a_id != person_b_id` (CHECK)
- `valid_to IS NULL OR valid_to >= valid_from` (CHECK)
- `normalized_pair` = `LEAST(person_a_id, person_b_id) || GREATEST(person_a_id, person_b_id)`

**Rules:**
- Relationship endpoints SHALL be Persons, never Users
- A Relationship SHALL connect exactly two different Persons
- One physical Relationship SHALL represent both perspectives (inverse is derived)
- RelationshipType SHALL be mandatory
- `valid_from` IS mandatory
- `valid_to` IS optional (NULL = ongoing)
- `valid_to` IS inclusive
- Future-effective relationships ARE supported
- Historical relationships ARE preserved
- No separate status field IS stored (status derived from dates)
- Self-relationships SHALL be rejected

**Derived Status:**
- Future: `today < valid_from`
- Effective: `valid_from <= today AND (valid_to IS NULL OR today <= valid_to)`
- Historical: `valid_to IS NOT NULL AND today > valid_to`

#### Scenario: Create Relationship

- **WHEN** admin creates a Relationship with person_a_id, person_b_id, relationship_type_id, valid_from
- **THEN** system SHALL validate both Persons exist
- **AND** system SHALL validate Persons are different (not self-relationship)
- **AND** system SHALL validate RelationshipType exists
- **AND** system SHALL validate no overlapping Relationship exists for the same Person pair
- **AND** system SHALL normalize Person IDs for symmetric relationships
- **AND** system SHALL create the Relationship

#### Scenario: Reject Self-Relationship

- **WHEN** admin attempts to create a Relationship where person_a_id = person_b_id
- **THEN** system SHALL reject with `SELF_RELATIONSHIP_NOT_ALLOWED` error

#### Scenario: Reject Overlapping Relationship

- **WHEN** admin attempts to create a Relationship for a Person pair that has an existing effective Relationship
- **THEN** system SHALL reject with `RELATIONSHIP_OVERLAP` error

#### Scenario: Symmetric Normalization

- **WHEN** admin creates a Relationship with a symmetric RelationshipType
- **THEN** system SHALL normalize `person_a_id = LEAST(person_a_id, person_b_id)`
- **AND** system SHALL normalize `person_b_id = GREATEST(person_a_id, person_b_id)`

#### Scenario: Derive Inverse Perspective

- **WHEN** user views a Relationship from Person B's perspective
- **THEN** system SHALL derive the inverse view using the RelationshipType's inverse

#### Scenario: Update Relationship Dates

- **WHEN** admin updates Relationship valid_from or valid_to
- **THEN** system SHALL validate the new dates do not invalidate existing ContactRoleAssignments
- **AND** if any role falls outside new validity, system SHALL reject with `RELATIONSHIP_TYPE_CHANGE_REQUIRES_RECONCILIATION` error

#### Scenario: End Relationship

- **WHEN** admin ends a Relationship
- **THEN** system SHALL set `valid_to` to the specified date
- **AND** Relationship SHALL be preserved (no hard delete)

---

### Requirement: ContactRoleAssignment Entity

A `ContactRoleAssignment` SHALL attach a ContactRole to a Relationship with independent temporal validity.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `relationship_id` (UUID, FK → relationship.id, NOT NULL)
- `contact_role_id` (UUID, FK → contact_role.id, NOT NULL)
- `valid_from` (DATE, NOT NULL)
- `valid_to` (DATE, NULLABLE)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Constraints:**
- `valid_to IS NULL OR valid_to >= valid_from` (CHECK)

**Rules:**
- A Relationship MAY have zero or more ContactRoleAssignments
- Role validity MUST be contained within parent Relationship validity
- Role start MAY differ from Relationship start
- Role end MAY differ from Relationship end
- The same ContactRole MAY have multiple non-contiguous periods
- Same-role periods MAY NOT overlap for the same Relationship
- Historical assignments SHALL be preserved (no hard delete)
- Ending a role SHALL require explicit `valid_to`

#### Scenario: Add ContactRole to Relationship

- **WHEN** admin adds a ContactRole to a Relationship
- **THEN** system SHALL validate ContactRole is compatible with RelationshipType
- **AND** system SHALL validate role dates are contained within Relationship dates
- **AND** system SHALL validate no overlap with existing same-role periods
- **AND** system SHALL create the ContactRoleAssignment

#### Scenario: Reject Role Outside Relationship

- **WHEN** admin adds a ContactRole with dates outside the Relationship validity
- **THEN** system SHALL reject with `CONTACT_ROLE_OUTSIDE_RELATIONSHIP` error

#### Scenario: Reject Overlapping Role Periods

- **WHEN** admin adds a ContactRole that overlaps with an existing same-role period
- **THEN** system SHALL reject with `CONTACT_ROLE_OVERLAP` error

#### Scenario: End ContactRole

- **WHEN** admin ends a ContactRoleAssignment
- **THEN** system SHALL set `valid_to` to the specified date
- **AND** assignment SHALL be preserved (no hard delete)

#### Scenario: Multiple Non-Contiguous Periods

- **WHEN** admin adds a ContactRole that was previously ended
- **THEN** system SHALL allow creating a new non-overlapping period for the same role

---

### Requirement: RelationshipType Change Validation

An existing Relationship MAY change its RelationshipType. The new type MUST be validated against all existing ContactRoleAssignments.

#### Scenario: Valid RelationshipType Change

- **WHEN** admin changes RelationshipType and all existing roles are compatible with new type
- **THEN** system SHALL allow the change

#### Scenario: Reject Incompatible RelationshipType Change

- **WHEN** admin changes RelationshipType and any existing role is incompatible with new type
- **THEN** system SHALL reject with `RELATIONSHIP_TYPE_CHANGE_REQUIRES_RECONCILIATION` error
- **AND** system SHALL identify the incompatible assignments
- **AND** system SHALL NOT silently delete roles

---

### Requirement: Relationship Resolution

The system SHALL support querying relationships from a Person's perspective.

#### Scenario: List Relationships for Person

- **WHEN** user requests relationships for a Person
- **THEN** system SHALL return all Relationships where person is person_a_id OR person_b_id
- **AND** system SHALL support filtering by RelationshipType
- **AND** system SHALL support filtering by effective date

#### Scenario: Resolve Related Persons

- **WHEN** user requests related Persons for a Person
- **THEN** system SHALL return the related Person records with relationship metadata

#### Scenario: List Effective ContactRoles

- **WHEN** user requests effective ContactRoles for a Relationship
- **THEN** system SHALL return only roles where `valid_from <= today AND (valid_to IS NULL OR today <= valid_to)`

---

### Requirement: Tenant Boundaries

C-06 SHALL respect the platform tenancy model.

**Rules:**
- All C-06 tables SHALL carry `client_id` for tenant isolation
- Relationships SHALL NOT be exposed across unauthorized tenant boundaries
- C-06 SHALL use existing RLS and C-04 authorization
- Cross-institution relationships are NOT implicitly allowed

#### Scenario: Tenant Isolation

- **WHEN** user queries relationships
- **THEN** system SHALL only return relationships belonging to the user's client

---

### Requirement: Audit Integration

Relationship mutations SHALL integrate with the platform audit capability.

**Events:**
- `relationship.created`
- `relationship.updated`
- `relationship.ended`
- `relationship.type_changed`
- `relationship.contact_role_added`
- `relationship.contact_role_updated`
- `relationship.contact_role_ended`

#### Scenario: Emit Audit Event on Relationship Creation

- **WHEN** a Relationship is created
- **THEN** system SHALL emit `relationship.created` audit event

#### Scenario: Emit Audit Event on ContactRole Addition

- **WHEN** a ContactRole is added to a Relationship
- **THEN** system SHALL emit `relationship.contact_role_added` audit event

---

## Seeded Data

### Default RelationshipTypes

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

### Default ContactRoles

| Code | Name |
|---|---|
| `primary_guardian` | Primary Guardian |
| `guardian` | Guardian |
| `financial_responsible` | Financial Responsible |
| `emergency_contact` | Emergency Contact |
| `pickup_authorized` | Pickup Authorized |

### Default Compatibility Matrix

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

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/relationship-types` | List relationship types |
| POST | `/api/v1/relationship-types` | Create relationship type (auto-generates inverse) |
| GET | `/api/v1/contact-roles` | List contact roles |
| GET | `/api/v1/contact-roles/compatible/{type_id}` | List compatible roles for a relationship type |
| GET | `/api/v1/people/{person_id}/relationships` | List relationships for a person |
| POST | `/api/v1/people/{person_id}/relationships` | Create relationship |
| GET | `/api/v1/relationships/{id}` | Get relationship details |
| PATCH | `/api/v1/relationships/{id}` | Update relationship (dates, type) |
| POST | `/api/v1/relationships/{id}/end` | End relationship |
| POST | `/api/v1/relationships/{id}/contact-roles` | Add contact role to relationship |
| PATCH | `/api/v1/contact-role-assignments/{id}` | Update contact role period |
| POST | `/api/v1/contact-role-assignments/{id}/end` | End contact role |

---

## Error Codes

| Code | Description |
|---|---|
| `PERSON_NOT_FOUND` | Person does not exist |
| `PERSON_SCOPE_VIOLATION` | Person outside allowed scope |
| `SELF_RELATIONSHIP_NOT_ALLOWED` | Cannot relate person to themselves |
| `RELATIONSHIP_TYPE_NOT_FOUND` | RelationshipType does not exist |
| `INVALID_RELATIONSHIP_TYPE` | Invalid RelationshipType for this operation |
| `INVERSE_RELATIONSHIP_TYPE_INVALID` | Inverse RelationshipType is invalid |
| `RELATIONSHIP_DATE_INVALID` | Invalid date parameters |
| `RELATIONSHIP_OVERLAP` | Overlapping relationship exists for this person pair |
| `RELATIONSHIP_NOT_FOUND` | Relationship does not exist |
| `CONTACT_ROLE_NOT_FOUND` | ContactRole does not exist |
| `CONTACT_ROLE_NOT_ALLOWED` | ContactRole not compatible with RelationshipType |
| `CONTACT_ROLE_DATE_INVALID` | Invalid date parameters |
| `CONTACT_ROLE_OUTSIDE_RELATIONSHIP` | Role dates outside Relationship validity |
| `CONTACT_ROLE_OVERLAP` | Overlapping same-role period exists |
| `RELATIONSHIP_TYPE_CHANGE_REQUIRES_RECONCILIATION` | Existing roles incompatible with new type |
