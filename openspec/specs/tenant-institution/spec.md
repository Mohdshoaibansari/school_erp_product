## Purpose

Multi-tenant root with institutions, org units, lifecycle management.

## Requirements

### Requirement: Multi-tenant structure
Feature: Tenant & Institution Management
Rule: Every client is a tenant. Every operational unit is an institution within a tenant.

#### Scenario: Create a new tenant
- **GIVEN** a platform owner
- **WHEN** they register a new client
- **THEN** a tenant record is created with status "active"
- **AND** an institution record is created as the first school

#### Scenario: Tenant can have multiple institutions
- **GIVEN** a tenant with one active institution
- **WHEN** they add a second institution
- **THEN** the second institution is created under the same tenant
- **AND** both institutions share the same tenant_id

#### Scenario: Tenant lifecycle states
- **GIVEN** an active tenant
- **WHEN** the tenant is suspended
- **THEN** all associated institutions are also suspended
- **AND** users from that tenant cannot log in

### Requirement: Institution lifecycle
Feature: Tenant & Institution Management
Rule: Institutions follow a lifecycle and are never hard-deleted

#### Scenario: Institution starts as onboarding
- **GIVEN** a new institution is created
- **WHEN** the setup wizard completes
- **THEN** the institution transitions to "active"
- **AND** users can now access it

#### Scenario: Institution can be archived
- **GIVEN** an active institution with historical data
- **WHEN** the institution is archived
- **THEN** all student and staff data is preserved as read-only
- **AND** the institution no longer appears in active lists
