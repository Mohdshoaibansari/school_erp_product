## 1. Project Setup

- [x] 1.1 Initialize pnpm workspace with monorepo structure (packages/database, packages/kernel, packages/shared, apps/api)
- [x] 1.2 Set up TypeScript, ESLint, Prettier across all packages
- [x] 1.3 Configure Prisma with PostgreSQL connection and tenant_id middleware
- [x] 1.4 Create initial Prisma schema with base fields (tenant_id, created_at, updated_at, deleted_at)

## 2. Tenant & Institution Service (C-01)

- [x] 2.1 Define Prisma models: tenants, institutions, org_units
- [x] 2.2 Implement TenantService: create, get, list, update, lifecycle transitions
- [x] 2.3 Implement InstitutionService: create, get, list, archive, reactivate
- [x] 2.4 Implement Prisma middleware that auto-filters tenant_id on all queries

## 3. Identity & Users Service (C-02)

- [x] 3.1 Define Prisma models: users, user_profiles, user_institutions, user_identifiers
- [x] 3.2 Implement UserService: create, get, getByEmail, list, update, assignToInstitution
- [x] 3.3 Implement user lifecycle: invited → active → suspended → archived
- [x] 3.4 Implement user profile management

## 4. Authentication Service (C-03)

- [x] 4.1 Implement email/password login with Argon2id hashing
- [x] 4.2 Implement JWT access token + refresh token generation

## 5. Authorization Service (C-04)

- [x] 5.1 Define Prisma models: roles, permissions, role_permissions, role_assignments
- [x] 5.2 Implement AuthZService: check, require, getUserPermissions, assignRole
- [x] 5.3 Define predefined roles: Director, Principal, Teacher, Parent, Student
- [x] 5.4 Implement scope resolution (institution, grade, class level)

## 6. Subscription Service (C-07)

- [x] 6.1 Define Prisma models: subscription_tiers, module_entitlements
- [x] 6.2 Implement SubscriptionService: getTier, getAvailableModules, checkStudentCap
- [x] 6.3 Define free tier: 100 student cap, 3 modules (Students, Attendance, Fees)
- [x] 6.4 Define paid tier: unlimited students, all modules
- [x] 6.5 Implement entitlement middleware helper for module gating

## 15. Code Quality Fixes

- [x] 15.1 Create missing barrel files (identity/index.ts, auth/index.ts, authorization/index.ts, subscription/index.ts)
- [x] 15.2 Fix tenant middleware thread safety (AsyncLocalStorage instead of global variable)
- [x] 15.3 Add soft delete filtering (deletedAt: null) to all getById, list, getByEmail methods
- [x] 15.4 Add validation to UserService (entity exists, input validation)
- [x] 15.5 Fix cross-tenant queries (getByStatus, getRoles, getPermissions must scope to tenant)
- [x] 15.6 Convert UserProfileService.delete to soft delete pattern
- [x] 15.7 Extract inline types to named interfaces (CreateRoleInput, CreateTierInput, etc.)
- [x] 15.8 Implement checkStudentCap with real student count query
