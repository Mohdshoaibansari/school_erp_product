## Purpose

Document the existing School ERP backend implementation covering core service patterns, lifecycle management, and tenant isolation architecture.

## Requirements

### Requirement: Tenant lifecycle documentation
Feature: Code Documentation SHALL describe the Tenant service implementation covering its full lifecycle and architectural role
Rule: The Tenant service implementation must be documented covering its full lifecycle and architectural role.

#### Scenario: Tenant creation bootstraps a first institution
- **GIVEN** the TenantService.create method
- **WHEN** a new tenant is created
- **THEN** the documentation describes that a "Main Campus" institution with ONBOARDING status is auto-created
- **AND** the documentation explains the tenant slug uniqueness constraint

#### Scenario: Tenant suspension cascades to institutions
- **GIVEN** the TenantService.suspend method
- **WHEN** a tenant is suspended
- **THEN** the documentation captures that all non-archived institutions are also suspended
- **AND** the documentation notes the atomicity boundary (single transaction)

#### Scenario: Soft delete preserves data
- **GIVEN** the archive methods on TenantService and InstitutionService
- **WHEN** a record is archived
- **THEN** the documentation describes the soft-delete pattern (deletedAt timestamp + ARCHIVED status)
- **AND** the documentation explains that queries filter deletedAt: null

#### Scenario: Tenant statistics aggregate institutions and users
- **GIVEN** the TenantService.getStats method
- **WHEN** statistics are requested
- **THEN** the documentation describes the aggregated counts returned (institutions, users)

### Requirement: Institution lifecycle documentation
Feature: Code Documentation MUST describe the Institution service implementation covering its status transitions and tenant scoping
Rule: The Institution service implementation must be documented covering its status transitions and tenant scoping.

#### Scenario: Institution has four status states
- **GIVEN** the InstitutionService implementation
- **WHEN** the lifecycle is documented
- **THEN** the documentation lists all statuses: ONBOARDING, ACTIVE, SUSPENDED, ARCHIVED
- **AND** the documentation maps valid transitions between statuses

#### Scenario: Institution creation validates tenant is active
- **GIVEN** the InstitutionService.create method
- **WHEN** documentation covers preconditions
- **THEN** it captures that the tenant must exist and have ACTIVE status
- **AND** it explains that new institutions start in ONBOARDING status

#### Scenario: Institution suspension enforces transition rules
- **GIVEN** the InstitutionService.suspend method
- **WHEN** documentation covers validation
- **THEN** it describes that institutions in ARCHIVED status cannot be suspended
- **AND** it describes that already-suspended institutions cannot be re-suspended

### Requirement: Multi-tenant isolation pattern documentation
Feature: Code Documentation MUST describe the tenant isolation middleware implementation, covering how tenant scoping is applied automatically
Rule: The tenant isolation middleware implementation must be documented, covering how tenant scoping is applied automatically.

#### Scenario: Prisma middleware auto-filters by tenantId
- **GIVEN** the tenant middleware in database/src/index.ts
- **WHEN** the isolation pattern is documented
- **THEN** the documentation explains that all TENANT_MODELS queries are auto-filtered by tenantId via AsyncLocalStorage
- **AND** the documentation lists which models skip tenant filtering (Tenant, OrgUnit, Permission)
- **AND** the documentation explains that write operations require a tenant context

#### Scenario: Tenant context uses AsyncLocalStorage
- **GIVEN** the TenantContext infrastructure
- **WHEN** the documentation covers context propagation
- **THEN** it describes the setTenantContext, getTenantContext, and runWithTenant helpers
- **AND** it explains the thread-safe nature of AsyncLocalStorage
