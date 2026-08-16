# Spec Delta — Tenant & Institution (ADDED frontend UI)

> **Change:** add-frontend-web-mobile-ui
> **Domain:** tenant-institution
> **Impact:** ADDED (net-new frontend C-01 UI)
> **Source:** `docs/architecture/adr-frontend-implementation.md` (D1, D5, D6), `docs/prd/frontend-web-mobile.md` (P1-AC-13..P1-AC-18)

---

## ADDED Requirements

### REQ-FE-TI-01: Platform Owner — Clients Screen

The app SHALL provide a Clients screen where the Platform Owner can list (searchable/filterable), view details, create, edit, and transition the lifecycle of clients (e.g., pending → active → suspended/closed), and view a client's institutions and users (P1-AC-13).

#### Scenario: Manage client lifecycle
- **WHEN** a Platform Owner acts on the Clients screen
- **THEN** they can list, create, edit, and transition client lifecycle state, and view the client's institutions and users

---

### REQ-FE-TI-02: Platform Owner — Institution Types Screen

The app SHALL provide an Institution Types catalog screen where the Platform Owner can list, create, and edit institution types. Deactivate is DEFERRED — the backend exposes no deactivate endpoint (P1-AC-14, ADR R10).

#### Scenario: Manage institution types
- **WHEN** a Platform Owner acts on the Institution Types screen
- **THEN** they can list, create, and edit institution types (deactivate deferred)

---

### REQ-FE-TI-03: Platform Owner — Ownership Transfer

The app SHALL provide an Ownership Transfers screen where the Platform Owner can initiate a transfer (moving an institution/client between owners), review and complete it, and see the transfer reflected in the affected tenant's ownership (P1-AC-15).

#### Scenario: Initiate and complete transfer
- **WHEN** a Platform Owner initiates and completes an ownership transfer
- **THEN** the transfer is reflected on the affected tenant

---

### REQ-FE-TI-04: Platform Owner — Client Users Screen

The app SHALL provide a Client Users screen (per client) where the Platform Owner can list, create, edit, and transition client users via `/api/v1/platform/clients/{client_id}/users` (P1-AC-16).

#### Scenario: Manage client users
- **WHEN** a Platform Owner acts on the client users screen
- **THEN** they can list, create, edit, and transition users under that client via the platform client-users endpoint

---

### REQ-FE-TI-05: Client Director — Institutions Screen

The app SHALL provide an Institutions screen (scoped to the director's client) where the Client Director can list, create, edit, transition the lifecycle, and trigger go-live of institutions (P1-AC-17).

#### Scenario: Manage institutions and go-live
- **WHEN** a Client Director acts on the Institutions screen
- **THEN** they can create, edit, transition, and go-live institutions under their client

---

### REQ-FE-TI-06: Client Director — Org Units Screen

The app SHALL provide an Org Units screen where the Client Director can view the org-unit tree (subtree navigation), create/edit org units, move them within the tree, reorder siblings, and archive/reactivate org units (P1-AC-18).

#### Scenario: Manage org-unit tree
- **WHEN** a Client Director acts on the Org Units screen
- **THEN** they can navigate the subtree, create/edit org units, move them, reorder siblings, and archive/reactivate them
