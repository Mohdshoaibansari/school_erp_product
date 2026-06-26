## 1. Tenant Service Documentation

- [x] 1.1 Document TenantService.create — auto-creates first institution, slug uniqueness, atomic setup
- [x] 1.2 Document TenantService lifecycle methods: suspend (cascade), reactivate, archive (soft delete)
- [x] 1.3 Document TenantService.getStats — aggregated institution/user counts
- [x] 1.4 Document tenant status transitions: ACTIVE → SUSPENDED → ARCHIVED, with validation rules

## 2. Institution Service Documentation

- [x] 2.1 Document InstitutionService.create — tenant must exist and be ACTIVE, starts ONBOARDING
- [x] 2.2 Document InstitutionService lifecycle: completeOnboarding, suspend, reactivate, archive
- [x] 2.3 Document institution status transitions with valid transition map
- [x] 2.4 Document InstitutionService.getActiveByTenant and getStats patterns

## 3. Multi-Tenant Isolation Documentation

- [x] 3.1 Document Prisma tenant middleware — auto-filtering by tenantId via AsyncLocalStorage
- [x] 3.2 Document models that skip tenant filtering (Tenant, OrgUnit, Permission) and why
- [x] 3.3 Document TenantContext helpers: setTenantContext, getTenantContext, runWithTenant
- [x] 3.4 Document tenant context requirement for write operations

## 4. ADR Review & Create

- [x] 4.1 Review existing ADRs (0001-0010) for accuracy against current Tenant & Institution code
- [x] 4.2 Create ADR for tenant isolation middleware pattern (new — no existing ADR covers this)
- [x] 4.3 Create ADR for Tenant service lifecycle and institution cascade behavior
- [x] 4.4 Validate all documentation against existing spec files

## 5. Validation

- [x] 5.1 Run `openspec validate document-existing-code --type change --strict`
