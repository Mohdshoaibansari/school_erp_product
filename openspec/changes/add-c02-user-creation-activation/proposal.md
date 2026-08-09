# Proposal: C-02 User Creation & Activation

> **Change ID:** `add-c02-user-creation-activation`
> **Status:** Proposed
> **Capability:** C-02 Identity & User Management (intersecting C-03 Authentication, C-08 Configuration Framework, Kernel/Auth infrastructure)
> **Source PRD:** `docs/prd/c-02-identity-user-management.md` (15 acceptance criteria)
> **Source ADR:** `docs/architecture/adr-c02-identity-user-management-implementation.md` (5 locked decisions D1–D5)
> **Impact Classification:** `docs/prd/c-02-impact-classification.md`

---

## 1. Summary

Unify the currently-disconnected user creation and activation paths so that **every user** — Client Director (`client_user`) and institution user (`app_user`) alike — follows the same lifecycle: **creation → invite → activate → login**. The work adds invite-JWT minting to `POST /api/v1/users`, consolidates all activation through a single `/api/auth/activate` endpoint, moves the invite URL from a hardcoded string to a config-driven key, and fixes three pre-existing production-blocking bugs on the activation path.

## 2. Why

| Problem | Impact |
|---------|--------|
| Institution users have NO backend activation path | Supabase `service_role` key exposed in journey-flow HTML; no audit logging; no lifecycle validation |
| `POST /api/v1/users` never mints an invite token | Two disconnected paths (CD bootstrap has tokens, institution users don't) |
| `/api/auth/activate` already has code for both tables but institution users never reach it | Gap is purely wiring, not architecture |
| Three production-blocking bugs on the activation path | `user_metadata` NameError, RLS session vars never set, `app.current_user_id` never populated |
| Hardcoded `http://127.0.0.1:8000` in invite URL construction | Violates AGENTS.md §8 (Config-First); breaks in non-dev environments |

## 3. What Changes

| Domain | Delta | Summary |
|--------|-------|---------|
| **identity-user-management** (C-02) | ADDED | `POST /api/v1/users` mints invite JWT, accepts optional `role_id`, returns `{user, invite_url}` |
| **authentication** (C-03) | MODIFIED | `/api/auth/activate` handles both user tables; response adds `user_tier` + `client_slug`, removes tokens |
| **configuration-framework** (C-08) | ADDED | New config key `app.activationBaseUrl` seeded via migration |
| **auth-infrastructure** (Kernel) | MODIFIED | Fix `user_metadata` NameError, add RLS session-var hook, populate `app.current_user_id` |
| **Journey Flows** | REMOVED | Supabase Admin API workaround retired; HTML updated for new response shapes |

## 4. Decisions Locked (from ADR)

| ID | Decision |
|----|----------|
| D1 | Unified activation flow for all user types — single creation + invite + activate chain |
| D2 | Optional `role_id` on `POST /api/v1/users` — assigned atomically at creation |
| D3 | Invite URL built from `app.activationBaseUrl` config key |
| D4 | Activate returns `{message, user_id, user_tier, client_slug}` — no JWT tokens |
| D5 | Three pre-existing bugs must be fixed as prerequisites |

## 5. Cross-References

| Artifact | Path |
|----------|------|
| PRD | `docs/prd/c-02-identity-user-management.md` |
| Impact Classification | `docs/prd/c-02-impact-classification.md` |
| ADR | `docs/architecture/adr-c02-identity-user-management-implementation.md` |
| Platform Capabilities | `docs/platform-capabilities/platform-capabilities-v3.md` §C-02, §C-03 |
| Functional Requirements | `docs/requirements/functional-requirements.md` §1.3, §1.4 |

## 6. Out of Scope

- Email delivery of invites (C-09, future)
- Bulk user import (future)
- Client Director self-registration (future)
- JWT tokens from `/api/auth/activate` (explicitly rejected per D4)
- `pending` lifecycle state removal (retained on state machine, bypassed in activate)
