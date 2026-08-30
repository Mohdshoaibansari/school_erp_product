## ADDED Requirements

### Requirement: Employee is a business resource linked to a person

The system SHALL represent an employee as a business resource that links to a `person` (the human anchor), never directly to an account. An employee MUST have a `person_id` and an `institution_id`.

#### Scenario: Employee links to person, not account

- **GIVEN** a person `P001` exists and has no login account
- **WHEN** an employee record is created for `P001`
- **THEN** the employee record references `P001` via `person_id`
- **AND** no `app_user` account is created or required

#### Scenario: Employee may coexist with a login account

- **GIVEN** a person `P001` has an `app_user` account
- **WHEN** an employee record is created for `P001`
- **THEN** the employee record references `P001` via `person_id`
- **AND** the employee record does not store credentials or session state

### Requirement: One employment relationship per person per institution

The system SHALL enforce at most one employee record per (person, institution). The same person MAY hold separate employee records at different institutions.

#### Scenario: Duplicate employment in the same institution is rejected

- **GIVEN** an employee record exists for person `P001` at institution `I001`
- **WHEN** a second employee record is created for `P001` at `I001`
- **THEN** the system rejects the creation with a uniqueness violation

#### Scenario: Same person employed at two institutions

- **GIVEN** an employee record exists for person `P001` at institution `I001`
- **WHEN** an employee record is created for `P001` at institution `I002`
- **THEN** the system accepts the creation as a distinct employee record with its own employee number and lifecycle

### Requirement: Employee number auto-generation

The system SHALL auto-generate an `employee_no` per institution using the format `EMP-{inst_code}-{seq:06d}`, unique within the institution, and it MUST NOT be nullable.

#### Scenario: Employee number generated on creation

- **GIVEN** institution `I001` has no employees
- **WHEN** the first employee is created at `I001`
- **THEN** the employee receives an `employee_no` matching `EMP-{inst_code}-000001`

#### Scenario: Employee number increments per institution

- **GIVEN** institution `I001` already has an employee numbered `EMP-{inst_code}-000001`
- **WHEN** a second employee is created at `I001`
- **THEN** the employee receives an `employee_no` of `EMP-{inst_code}-000002`

### Requirement: Employment type

The system SHALL restrict `employment_type` to the values `FULL_TIME`, `PART_TIME`, `CONTRACT`, `TEMPORARY`, `INTERN`, and `CONSULTANT`, enforced at the database level.

#### Scenario: Valid employment type accepted

- **GIVEN** a request to create an employee
- **WHEN** `employment_type` is `FULL_TIME`
- **THEN** the employee is created with `employment_type` set to `FULL_TIME`

#### Scenario: Invalid employment type rejected

- **WHEN** `employment_type` is a value outside the allowed set
- **THEN** the system rejects the request with a validation error

### Requirement: Employee lifecycle states

The system SHALL support seven employment states — `Hired`, `Active`, `On-Leave`, `Suspended`, `Retired`, `Resigned`, `Terminated` — and MUST start a new employee in `Hired`.

#### Scenario: New employee starts as Hired

- **WHEN** an employee is created
- **THEN** the employee's `employment_status` is `Hired`

### Requirement: Employee activation

The system SHALL allow a non-terminal employee to transition to `Active` via the activate operation.

#### Scenario: Activate from Hired

- **GIVEN** an employee in status `Hired`
- **WHEN** the activate operation is invoked
- **THEN** the employee's `employment_status` becomes `Active`

#### Scenario: Activate returns a suspended or on-leave employee to Active

- **GIVEN** an employee in status `Suspended` or `On-Leave`
- **WHEN** the activate operation is invoked
- **THEN** the employee's `employment_status` becomes `Active`

#### Scenario: Terminal employee cannot be activated

- **GIVEN** an employee in status `Terminated`, `Resigned`, or `Retired`
- **WHEN** the activate operation is invoked
- **THEN** the system rejects the transition as invalid

### Requirement: Employee suspension and deactivation

The system SHALL support reversible transitions from `Active` to `Suspended` (suspend) and from `Active` to `On-Leave` (deactivate).

#### Scenario: Suspend an active employee

- **GIVEN** an employee in status `Active`
- **WHEN** the suspend operation is invoked
- **THEN** the employee's `employment_status` becomes `Suspended`

#### Scenario: Deactivate an active employee

- **GIVEN** an employee in status `Active`
- **WHEN** the deactivate operation is invoked
- **THEN** the employee's `employment_status` becomes `On-Leave`

### Requirement: Employee termination

The system SHALL transition an `Active` employee to a terminal state (`Terminated`, `Resigned`, or `Retired`) via the terminate operation using a `terminal_status` field, and MUST reject transitions from already-terminal employees.

#### Scenario: Terminate with resignation

- **GIVEN** an employee in status `Active`
- **WHEN** the terminate operation is invoked with `terminal_status = resigned`
- **THEN** the employee's `employment_status` becomes `Resigned`

#### Scenario: Terminate with retirement

- **GIVEN** an employee in status `Active`
- **WHEN** the terminate operation is invoked with `terminal_status = retired`
- **THEN** the employee's `employment_status` becomes `Retired`

#### Scenario: Invalid terminal_status rejected

- **WHEN** the terminate operation is invoked with a `terminal_status` outside `resigned`, `terminated`, or `retired`
- **THEN** the system rejects the request with a validation error

### Requirement: Terminal transition cascades to the account

The system SHALL archive the linked `app_user` account whose `institution_id` matches the employee's institution when an employee transitions to `Resigned`, `Terminated`, or `Retired`, in the same transaction, via the `person` link. Reversible transitions MUST NOT cascade.

#### Scenario: Resignation archives the institution account

- **GIVEN** an employee linked to person `P001` who has an `app_user` account at institution `I001`
- **WHEN** the employee transitions to `Resigned` at `I001`
- **THEN** the `app_user` account at `I001` is archived

#### Scenario: Resignation does not archive a different institution's account

- **GIVEN** a person `P001` who is an employee at `I001` and `I002`, with separate accounts at each
- **WHEN** the `I001` employee transitions to `Resigned`
- **THEN** only the `I001` account is archived, and the `I002` account remains active

#### Scenario: Reversible transition does not cascade

- **GIVEN** an employee with a linked account
- **WHEN** the employee transitions to `Suspended` or `On-Leave`
- **THEN** no account is archived

### Requirement: Department and designation validation

The system SHALL validate `department` and `designation` against the configured allowed-value lists (`employee.departments` and `employee.designations`).

#### Scenario: Valid department accepted

- **GIVEN** `employee.departments` includes `Mathematics`
- **WHEN** an employee is created or updated with `department = Mathematics`
- **THEN** the value is accepted

#### Scenario: Department outside the configured list rejected

- **GIVEN** `employee.departments` does not include `Astrophysics`
- **WHEN** an employee is created or updated with `department = Astrophysics`
- **THEN** the system rejects the request with a validation error

### Requirement: Employee authorization

The system SHALL enforce authorization on every employee operation through the AuthZ Kernel using `employee.*` permissions scoped to the institution, treating the authenticated user as the subject and the employee as the protected resource.

#### Scenario: Authorized role allowed

- **GIVEN** a user with the `Admin` role (holding `employee.*` permissions) at institution `I001`
- **WHEN** the user performs an employee operation at `I001`
- **THEN** the operation is allowed

#### Scenario: Unauthorized role denied

- **GIVEN** a user with a role holding only `employee.read`
- **WHEN** the user attempts an `employee.terminate` operation
- **THEN** the operation is denied

#### Scenario: Wrong institution denied

- **GIVEN** a user authorized at institution `I001`
- **WHEN** the user attempts to operate on an employee at institution `I002`
- **THEN** the operation is denied

#### Scenario: Platform owner denied operational employee data

- **GIVEN** a platform owner
- **WHEN** the platform owner attempts to read or modify operational employee data
- **THEN** the operation is denied

### Requirement: Employee RLS isolation

The system SHALL enforce PostgreSQL row-level security on the `employee` table so that one client or institution can never read another's employee rows.

#### Scenario: Cross-institution read blocked

- **GIVEN** an employee at institution `I002`
- **WHEN** a user scoped to institution `I001` queries employees
- **THEN** the `I002` employee is not returned

#### Scenario: Cross-client read blocked

- **GIVEN** an employee belonging to client `C002`
- **WHEN** a user scoped to client `C001` queries employees
- **THEN** the `C002` employee is not returned

### Requirement: Employee listing and search

The system SHALL support listing employees with filtering by status, employment type, department, and designation, plus text search and pagination.

#### Scenario: Filter by employment status

- **GIVEN** employees in `Active` and `On-Leave` states
- **WHEN** employees are listed with a status filter of `Active`
- **THEN** only `Active` employees are returned

#### Scenario: Search by employee number or name

- **GIVEN** an employee with a known `employee_no`
- **WHEN** employees are searched by that number
- **THEN** the matching employee is returned
