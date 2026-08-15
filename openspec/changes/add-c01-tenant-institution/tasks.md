# Task Breakdown: Capability C-01 Tenant & Institution Management

## 1. Database Schema & Migration Setup
- [ ] 1.1 Create Alembic migration for lookup tables (`legal_entity_type`, `org_unit_type`, `institution_type_name`).
- [ ] 1.2 Create Alembic migration for core tables (`client`, `institution_type`, `institution`, `org_unit`) with UUID v4 primary keys.
- [ ] 1.3 Create Alembic migration for approval and lifecycle event tables (`approval`, `client_lifecycle_events`, `institution_lifecycle_events`, `ownership_transfer_events`).
- [ ] 1.4 Add Postgres Row-Level Security (RLS) policies on tenant-scoped tables (`client_id` filter) and self-visible RLS policy on `client` table.
- [ ] 1.5 Seed initial configurable lookup values and default system `institution_type` templates.

## 2. Core Repositories & Isolation Layer
- [ ] 2.1 Build base TenantContext middleware to extract `client_id` from subdomain and `selected_institution_id` from JWT.
- [ ] 2.2 Implement generic tenant-aware repository abstraction injecting `client_id` filter automatically into all SQL queries.
- [ ] 2.3 Implement Client repository (`get_by_slug`, `get_by_id`, `create`, `update_status`).
- [ ] 2.4 Implement Institution repository (`create_with_template`, `list_by_client`, `get_by_id`, `update_status`).
- [ ] 2.5 Implement OrgUnit repository with recursive CTE queries for subtree retrieval and `parent_id` hierarchy updates.

## 3. Application Services & Business Logic
- [ ] 3.1 Implement Client service (slug validation, reserved slug checking, immutability enforcement, lifecycle state machine D8).
- [ ] 3.2 Implement Institution service (template materialization engine, effective-state runtime gating against Client state D9).
- [ ] 3.3 Implement OrgUnit service (archive-only soft delete, type immutability validation, app-side cycle-prevention algorithm Q6).
- [ ] 3.4 Implement Approval flow service (pending approval creation, status transitions Q3).
- [ ] 3.5 Implement Ownership Transfer service (single-transaction atomic update across Client/Institution/OrgUnit/C-02/C-05 tables, audit event emission D12).

## 4. API Endpoints & Permission Wiring
- [ ] 4.1 Implement subdomain-resolved Client APIs (`GET /api/v1/client/self`).
- [ ] 4.2 Implement subdomain-resolved Institution APIs (`GET /api/v1/institutions`, `POST /api/v1/institutions`, `PATCH /api/v1/institutions/{id}`).
- [ ] 4.3 Implement OrgUnit management APIs (`GET /api/v1/institutions/{id}/org-units`, `POST /api/v1/institutions/{id}/org-units`, `PATCH /api/v1/org-units/{id}/move`, `POST /api/v1/org-units/{id}/archive`).
- [ ] 4.4 Implement Platform Owner APIs (`POST /api/v1/platform/clients`, `POST /api/v1/platform/clients/{id}/lifecycle-transition`, `POST /api/v1/platform/institution-types`, `POST /api/v1/platform/ownership-transfers`).
- [ ] 4.5 Wire Casbin AuthZ policies for D11 permission matrix enforcement across all endpoints.

## 5. Verification & Test Suite
- [ ] 5.1 Write unit tests for Client slug validation, reserved slug rejection, and slug immutability.
- [ ] 5.2 Write unit tests for Client lifecycle state machine (D8) and Institution lifecycle state machine (D9).
- [ ] 5.3 Write unit tests for OrgUnit application-side cycle-prevention algorithm.
- [ ] 5.4 Write integration tests for template materialization during institution creation.
- [ ] 5.5 Write integration tests for Postgres RLS policies and repository isolation verification.
- [ ] 5.6 Write end-to-end single-transaction integration test for Institution Ownership Transfer and historical audit event immutability.
