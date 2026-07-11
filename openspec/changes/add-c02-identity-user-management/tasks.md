# Implementation Tasks — C-02 Identity & User Management

> **Traceability.** Each task traces to grill-me decision IDs (Decisions 1–11) and PRD AC IDs (AC-1..AC-20). Tasks are grouped by concern and ordered by dependency. This is a checklist for the apply phase — no implementation is performed here.
>
> **Stack & architecture note.** The platform tech-stack ADR locks the stack (Postgres+Supabase, Python+FastAPI, SQLAlchemy 2.0+Alembic, Supabase Auth JWT, Casbin RBAC+ABAC, pytest). The platform software-architecture ADR locks the modular-monolith + module-manifest + monorepo structure (A1–A11). C-02 follows C-01's established patterns exactly.
>
> **References:** proposal.md, specs/identity-user-management/spec.md, design.md; PRD `docs/prd/c-02-identity-user-management.md`; C-01 spec `openspec/specs/tenant-institution/spec.md`; C-01 design `openspec/changes/archive/2026-07-08-add-c01-tenant-institution/design.md`.

## 1. Module structure & manifest (A5, AC-16)

> C-02 is a business-tier module (A2). It registers via the ModuleManifest Protocol (A5). The manifest hooks are invoked by the app factory in dependency order.

- [ ] 1.1 Create the C-02 module directory structure under `/backend/business/identity_user_management/` with `__init__.py`, `manifest.py`, `models/`, `repos/`, `routes/`, `services/`, `policies.py`, `dependencies.py`. — evidence: directory structure exists; `__init__.py` files importable.
- [ ] 1.2 Implement `IdentityUserManagementManifest` (subclass of `ManifestBase`) with `register_routes`, `register_casbin_policies`, `on_startup`, `on_shutdown`, `register_cli` hooks. Create a `manifest` singleton. — evidence: `manifest.py` exists; `manifest` object importable; `register_routes` and `register_casbin_policies` hooks callable.
- [ ] 1.3 Register C-02 manifest in the app factory's module list (after C-01, in dependency order). — evidence: `test_app_boots_with_c02_manifest` passes; C-02 routes mounted.

## 2. Database schema — C-02 entity tables (Decision 4, AC-4) — Alembic migration `002_c02_identity_user_management.py`

> All C-02 migrations live in the single Alembic env at `/backend/migrations/` (A7) under filenames prefixed `002_c02_*`. RLS policies are written as raw SQL inside the same Alembic migration.

- [ ] 2.1 Create the `user_category` lookup table (`id` UUID v4 PK, `name` unique). — evidence: migration creates `user_category` table; `test_user_category_pk_is_uuid_v4` + `test_user_category_name_unique` pass.
- [ ] 2.2 Create the `role` lookup table (`id` UUID v4 PK, `name` unique). — evidence: migration creates `role` table; `test_role_pk_is_uuid_v4` + `test_role_name_unique` pass.
- [ ] 2.3 Create the `user` table (`id` UUID v4 PK, `client_id` FK + RLS, `institution_id` FK, `email` globally unique, `name`, `user_category_id` FK → user_category, `lifecycle_status`, `created_at`, `updated_at`). — evidence: migration creates `user` table; `test_user_pk_is_uuid_v4` + `test_user_email_unique` + `test_user_has_client_id` + `test_user_has_institution_id` pass.
- [ ] 2.4 Create the `user_profile` table (`id` UUID v4 PK, `user_id` FK unique (1:1), `photo`, `date_of_birth`, `gender`, `blood_group`, `created_at`, `updated_at`). — evidence: migration creates `user_profile` table; `test_user_profile_pk_is_uuid_v4` + `test_user_profile_unique_user` pass.
- [ ] 2.5 Create the `role_assignment` table (`id` UUID v4 PK, `client_id` FK + RLS, `user_id` FK, `role_id` FK, `scope`, `created_at`, `updated_at`). — evidence: migration creates `role_assignment` table; `test_role_assignment_pk_is_uuid_v4` + `test_role_assignment_has_client_id` pass.
- [ ] 2.6 Create the `user_identifier` table (`id` UUID v4 PK, `client_id` FK + RLS, `user_id` FK, `type`, `value`, `created_at`, `updated_at`). — evidence: migration creates `user_identifier` table; `test_user_identifier_pk_is_uuid_v4` + `test_user_identifier_has_client_id` pass.
- [ ] 2.7 Create the `user_lifecycle_event` table (`id` UUID v4 PK, `client_id` FK + RLS, `user_id` FK, `state`, `reason`, `actor`, `entered_at`). — evidence: migration creates `user_lifecycle_event` table; `test_user_lifecycle_event_pk_is_uuid_v4` + `test_user_lifecycle_event_has_client_id` pass.

## 3. Database schema — seed data (Decision 9, Decision 10, R6)

> Seed data for UserCategory and Role lookup tables, inserted in the same Alembic migration.

- [ ] 3.1 Seed UserCategory lookup data: Learner, Academic Staff, Academic Leadership, Administrative Staff, Executive Leadership. — evidence: migration inserts 5 rows into `user_category`; `test_user_category_seed_data` passes.
- [ ] 3.2 Seed Role lookup data: Teacher, HOD, Principal, Student, Parent, Staff, Admin. — evidence: migration inserts 7 rows into `role`; `test_role_seed_data` passes.

## 4. Database schema — RLS policies (Decision 1, AC-1, AC-20) — raw SQL inside the same Alembic migration

> RLS policies are emitted as `CREATE POLICY` raw SQL inside `002_c02_*` Alembic migration files. Same pattern as C-01.

- [ ] 4.1 Enable RLS and create a `client_id`-matching policy on every tenant-scoped C-02 table (`user`, `role_assignment`, `user_identifier`, `user_lifecycle_event`). — evidence: migration enables FORCE RLS + creates policies on 4 tenant-scoped tables; `test_cross_tenant_isolation_user` + `test_cross_tenant_isolation_role_assignment` pass.
- [ ] 4.2 Verify `user_profile` does NOT have its own RLS policy (it's accessed via User FK, not directly queried by client_id). — evidence: `test_user_profile_no_rls_policy` inspects policy expressions; profile is accessed through User relationship.
- [ ] 4.3 Verify `user_category` and `role` lookup tables do NOT have RLS policies (they are global/shared, not tenant-scoped). — evidence: `test_user_category_no_rls` + `test_role_no_rls` pass.

## 5. Models — SQLAlchemy ORM models (Decision 4, Decision 5, Decision 6, Decision 7, Decision 8)

> Models live under `/backend/business/identity_user_management/models/`. Each model inherits from `kernel.db.Base`. DTOs are separate from ORM objects (repos return DTOs).

- [ ] 5.1 Implement `UserCategory` ORM model (`id`, `name`). — evidence: `models/user_category.py` exists; `test_user_category_model_fields` passes.
- [ ] 5.2 Implement `Role` ORM model (`id`, `name`). — evidence: `models/role.py` exists; `test_role_model_fields` passes.
- [ ] 5.3 Implement `User` ORM model (`id`, `client_id`, `institution_id`, `email`, `name`, `user_category_id`, `lifecycle_status`, `created_at`, `updated_at`). FK to `UserCategory`. — evidence: `models/user.py` exists; `test_user_model_fields` + `test_user_model_fk_user_category` pass.
- [ ] 5.4 Implement `UserProfile` ORM model (`id`, `user_id`, `photo`, `date_of_birth`, `gender`, `blood_group`, `created_at`, `updated_at`). FK to `User` (1:1). — evidence: `models/user_profile.py` exists; `test_user_profile_model_fields` + `test_user_profile_model_fk_user` pass.
- [ ] 5.5 Implement `RoleAssignment` ORM model (`id`, `client_id`, `user_id`, `role_id`, `scope`, `created_at`, `updated_at`). FK to `User` and `Role`. — evidence: `models/role_assignment.py` exists; `test_role_assignment_model_fields` + `test_role_assignment_model_fks` pass.
- [ ] 5.6 Implement `UserIdentifier` ORM model (`id`, `client_id`, `user_id`, `type`, `value`, `created_at`, `updated_at`). FK to `User`. — evidence: `models/user_identifier.py` exists; `test_user_identifier_model_fields` + `test_user_identifier_model_fk_user` pass.
- [ ] 5.7 Implement `UserLifecycleEvent` ORM model (`id`, `client_id`, `user_id`, `state`, `reason`, `actor`, `entered_at`). FK to `User`. — evidence: `models/user_lifecycle_event.py` exists; `test_user_lifecycle_event_model_fields` + `test_user_lifecycle_event_model_fk_user` pass.
- [ ] 5.8 Implement DTOs for all C-02 entities (UserDTO, UserProfileDTO, RoleAssignmentDTO, UserIdentifierDTO, etc.) under `services/dtos.py`. — evidence: `services/dtos.py` exists; DTOs are Pydantic BaseModel subclasses; `test_dto_serialization` passes.

## 6. Lifecycle state machine (Decision 8, AC-10, AC-11)

> State machine lives under `/backend/business/identity_user_management/services/state_machine.py`. Same pattern as C-01's `services/state_machine.py`.

- [ ] 6.1 Implement User lifecycle state machine: states (Invited, Pending, Active, Suspended, Archived), arcs (Invited→Pending, Pending→Active, Active→Suspended, Suspended→Active, Active→Archived, Suspended→Archived), Archived terminal. — evidence: `services/state_machine.py` (USER_ARCS, validate_user_transition); `test_user_lifecycle_all_arcs_accepted` + `test_user_lifecycle_archived_terminal` + `test_user_lifecycle_disallowed_arc_rejected` pass.
- [ ] 6.2 Implement lifecycle event recording: every transition writes a `user_lifecycle_event` row with `state`, `reason`, `actor`, `entered_at`. — evidence: `repos/user_repo.py::transition_lifecycle` writes event rows; `test_user_lifecycle_event_recording` passes.

## 7. Repository layer — tenant-aware data access (Decision 1, AC-1, AC-17)

> C-02 repos live under `/backend/business/identity_user_management/repos/`. Repos inherit `TenantAwareRepositoryBase` from `kernel/repo_base.py`. Repos return DTOs, not ORM objects.

- [ ] 7.1 Implement `UserRepository` (inherits `TenantAwareRepositoryBase[User]`). Methods: `create`, `get`, `list`, `update`, `transition_lifecycle`. Auto-injects `client_id` from TenantContext. Returns UserDTO. — evidence: `repos/user_repo.py` exists; `test_user_repo_create` + `test_user_repo_list_filters_by_client_id` + `test_user_repo_returns_dtos` pass.
- [ ] 7.2 Implement `UserProfileRepository` (inherits `TenantAwareRepositoryBase[UserProfile]`). Methods: `create`, `get`, `update`. Returns UserProfileDTO. — evidence: `repos/user_profile_repo.py` exists; `test_user_profile_repo_create` + `test_user_profile_repo_get` pass.
- [ ] 7.3 Implement `RoleAssignmentRepository` (inherits `TenantAwareRepositoryBase[RoleAssignment]`). Methods: `create`, `get`, `list`, `delete`. Returns RoleAssignmentDTO. — evidence: `repos/role_assignment_repo.py` exists; `test_role_assignment_repo_create` + `test_role_assignment_repo_list` pass.
- [ ] 7.4 Implement `UserIdentifierRepository` (inherits `TenantAwareRepositoryBase[UserIdentifier]`). Methods: `create`, `get`, `list`, `delete`. Returns UserIdentifierDTO. — evidence: `repos/user_identifier_repo.py` exists; `test_user_identifier_repo_create` + `test_user_identifier_repo_list` pass.

## 8. Service layer — published interface (Decision 1–11, A4)

> Services live under `/backend/business/identity_user_management/services/`. Services orchestrate repos + TenantContext. Endpoints call services; services call repos. This is the module boundary other modules see.

- [ ] 8.1 Implement `IdentityUserService` with methods: `create_user`, `get_user`, `list_users`, `update_user`, `transition_lifecycle`, `create_profile`, `get_profile`, `update_profile`, `create_role_assignment`, `list_role_assignments`, `delete_role_assignment`, `create_identifier`, `list_identifiers`, `delete_identifier`. — evidence: `services/service.py` exists; `test_service_create_user` + `test_service_list_users` + `test_service_transition_lifecycle` pass.
- [ ] 8.2 Wire audit emission via `AuditEmitter` Protocol for: user creation, lifecycle transitions, role assignment/removal, identifier creation/deletion. — evidence: `test_audit_emission_user_created` + `test_audit_emission_lifecycle_transition` + `test_audit_emission_role_assignment` + `test_audit_emission_identifier_created` pass.

## 9. API layer — routes (Decision 1–11, A6, AC-16)

> Routes live under `/backend/business/identity_user_management/routes/`. Routes registered via the manifest `register_routes` hook (A5). Endpoints read `TenantContext` via `Depends(get_tenant_context)` (A6).

- [ ] 9.1 Implement User CRUD endpoints: create User, get User, list Users (with filters: UserCategory, Role, lifecycle status), update User. — evidence: `routes/users.py` exists; `test_create_user` + `test_get_user` + `test_list_users` + `test_update_user` pass.
- [ ] 9.2 Implement User lifecycle endpoints: transition lifecycle (Invited→Pending→Active→Suspended→Archived). — evidence: `routes/users.py`; `test_transition_user_lifecycle` + `test_transition_user_lifecycle_archived_terminal` pass.
- [ ] 9.3 Implement UserProfile endpoints: create profile, get profile, update profile. — evidence: `routes/profiles.py` exists; `test_create_profile` + `test_get_profile` + `test_update_profile` pass.
- [ ] 9.4 Implement RoleAssignment endpoints: create assignment, list assignments, delete assignment. — evidence: `routes/roles.py` exists; `test_create_role_assignment` + `test_list_role_assignments` + `test_delete_role_assignment` pass.
- [ ] 9.5 Implement UserIdentifier endpoints: create identifier, list identifiers, delete identifier. — evidence: `routes/identifiers.py` exists; `test_create_identifier` + `test_list_identifiers` + `test_delete_identifier` pass.
- [ ] 9.6 Implement UserCategory and Role lookup endpoints: list categories, list roles. — evidence: `routes/lookups.py` exists; `test_list_user_categories` + `test_list_roles` pass.

## 10. Dependencies — FastAPI dependency injection (A6)

> Dependencies live under `/backend/business/identity_user_management/dependencies.py`. Same pattern as C-01's `dependencies.py`.

- [ ] 10.1 Implement `get_identity_user_service()` dependency (returns the service singleton). — evidence: `dependencies.py` exists; `test_dependency_get_service` passes.
- [ ] 10.2 Wire dependencies in route handlers via `Depends(get_identity_user_service)`. — evidence: all route handlers use `Depends`; `test_route_dependency_wiring` passes.

## 11. Integration tests — end-to-end scenarios (AC-1..AC-20)

> Integration tests verify the full request flow: middleware → route → service → repo → database.

- [ ] 11.1 Test full user creation flow: create User → create UserProfile → create RoleAssignment → create UserIdentifier. — evidence: `test_integration_full_user_onboarding` passes.
- [ ] 11.2 Test tenant isolation: User at School A cannot see User at School B. — evidence: `test_integration_cross_tenant_isolation` passes.
- [ ] 11.3 Test lifecycle flow: Invited → Pending → Active → Suspended → Active → Archived. — evidence: `test_integration_full_lifecycle_flow` passes.
- [ ] 11.4 Test email uniqueness: duplicate email rejected across institutions and clients. — evidence: `test_integration_email_uniqueness` passes.
- [ ] 11.5 Test lookup tables: UserCategory and Role are queryable and usable for FK validation. — evidence: `test_integration_lookup_tables` passes.
