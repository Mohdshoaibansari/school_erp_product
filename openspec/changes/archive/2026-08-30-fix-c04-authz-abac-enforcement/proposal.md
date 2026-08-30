# Proposal — AuthZ Kernel ABAC Enforcement & Platform Owner Security Fix

**Product:** Multi-Tenant School ERP
**Capability:** C-04 Authorization / AuthZ Kernel
**Change ID:** `fix-c04-authz-abac-enforcement`
**Status:** Proposed
**Source brief:** Principal Architect security-fix task brief
**Baseline:** `add-c04-authz-abac-enhancement` (applied, unarchived) + consolidated C-04

---

## 1. Context

The AuthZ Kernel was recently enhanced with `SubjectContext`, `ResourceContext`,
`AuthorizationRequest`, `AuthorizationDecision`, attribute providers, provider
registry, conditional policies, ABAC attributes, and multiple-role support.
That implementation is on `main` and must not be discarded.

Current-state exploration found:

1. **`casbin_model.conf` matcher already references `match_attrs(r.sub, p.attrs)`**
   — the 5th policy field is in the matcher. However:
   - One ABAC DENY test (`test_failed_abac`) is a **vacuous stub** (no assertion).
   - There is **no raw-enforcer-boundary test** proving attribute=false or
     attribute=missing yields DENY *inside the Casbin matcher*.
   - Production conditional-policy registration hooks are `pass`
     (`manifest.register_authorization_policies`), so the enforcement path is
     exercised only by tests.
2. **Unconditional Platform Owner bypass exists in TWO places**:
   - `authorization_service.py:100–105` (modern path — returns ALLOW before Casbin).
   - `dependencies.py:230` (legacy fallback when service singleton is None).
3. **Platform Owner has NO platform-level Casbin permissions in production**:
   - Only `config.*` (8 perms, migration 009) are seeded for the PO role.
   - No `platform.*` permissions exist.
   - `client.*` has 4 perms (client.read/update/transfer_ownership/transition_lifecycle).
   - The D11 wildcard `("platform_owner", "*", "*", "any", "")` exists only in
     test fixtures, not production.
4. `_extract_policy_id` derives `role:resource:action:scope` and does NOT include
   `attrs`, so multiple conditional policies sharing a signature collide (P1).

## 2. Objectives

### P0 — Required
- Actually enforce ABAC attributes inside Casbin (verify + complete the matcher
  path: `match_attrs` participates; attr=false and attr=missing → DENY; attr=true
  → ALLOW; no-attr → normal RBAC/scope).
- Remove the unconditional Platform Owner authorization bypass (both locations).
- Preserve the existing tenant/institution authorization model (scope semantics:
  `any` / `tenant` / `institution`).
- Preserve multiple-role support (loop per effective role; a valid permission
  from any role may satisfy, subject to scope + ABAC).
- Preserve the existing Attribute Provider architecture (provider contract,
  registry, request-scoped caching, lazy resolution).
- Preserve fail-closed behavior (missing/unresolved/unknown attributes → DENY;
  provider failure → DENY).
- ABAC must never bypass RBAC (a positive attribute never grants a missing
  permission).
- Add regression/security tests proving the fixes.

### P1 — Recommended (only if a clean solution exists without destabilizing)
- Improve multi-role attribute resolution efficiency without changing semantics.
- Improve policy identification so conditional policies can be distinguished
  (`_extract_policy_id` should include `attrs` or use the actual matched policy).

## 3. Architectural Invariant

The AuthZ Kernel remains business-domain agnostic. No dependencies from AuthZ
into Teacher/Student/Parent/Academic/Homework/Attendance. No business ORM imports.

```
Authentication → TenantContext → Business Module → Authorization Request
→ AuthZ Kernel → Attribute Providers → Casbin → ALLOW/DENY
→ Business Service → PostgreSQL RLS
```

## 4. Platform Owner Product Requirement

- PO is a platform-level administrative identity.
- PO SHALL be evaluated through the normal authorization pipeline (Permission →
  Scope → ABAC → Casbin). No `if is_platform_owner: return ALLOW`.
- PO access to platform/client resources (client management, platform config,
  client metadata) is governed by the existing permission matrix
  (`client.*`, `config.*`).
- PO SHALL NOT automatically gain access to institute operational data
  (student, teacher, attendance, homework, etc.).
- The exact permission matrix continues to come from the existing
  authorization configuration/specification — no hardcoded business-resource
  list inside the Kernel, no invented permissions.
- Do not change RLS policies to facilitate PO access; the fix is at the
  authorization layer only.

## 5. Acceptance Criteria (Definition of Done)

- [ ] Casbin matcher actually evaluates the policy attribute requirement
      (`p.attrs` participates in the decision).
- [ ] attribute=true can satisfy a conditional policy → ALLOW.
- [ ] attribute=false cannot satisfy a conditional policy → DENY.
- [ ] attribute=missing fails closed → DENY.
- [ ] RBAC remains mandatory (positive attributes never grant missing permissions).
- [ ] Scope remains mandatory where required (tenant/client, institution).
- [ ] Platform Owner no longer has an unconditional ALLOW.
- [ ] Platform Owner is evaluated through the normal authorization mechanism.
- [ ] Platform Owner cannot automatically access institute operational resources.
- [ ] Existing platform/client access continues to work per configured permissions.
- [ ] Multiple roles continue to work (`[Principal, Teacher]`, `[HOD, Teacher]`).
- [ ] Existing provider architecture remains intact.
- [ ] Provider failures fail closed.
- [ ] No business module introduced into the Kernel; no business ORM imports.
- [ ] Existing RLS remains intact.
- [ ] Existing AuthZ tests pass; new ABAC regression tests pass; Platform Owner
      security tests pass; full relevant test suite passes.

## 6. Required Tests

### ABAC regression (raw enforcement boundary + pipeline)
1. attribute=true with required-attr policy → ALLOW
2. attribute=false with required-attr policy → DENY
3. attribute=missing with required-attr policy → DENY (fail-closed)
4. no attribute requirement → normal RBAC/scope evaluation (ALLOW when permitted)
5. ABAC must not bypass RBAC (attribute=true, permission absent → DENY)

### Platform Owner security
- PO + `client.read` platform/client resource → ALLOW
- PO → institute operational resource (student/teacher/attendance/homework) → DENY

### Scope regression
- Client A → Client A ALLOW; Client A → Client B DENY
- Institution A → Institution A ALLOW; Institution A → Institution B DENY

### Multi-role regression
- `[Principal, Teacher]` continues to work per existing policy semantics.

### Provider failure
- provider exception → DENY

## 7. Non-Goals

- No Teacher/Student/Parent business-rule implementation.
- No generic tenant-configurable rule engine.
- No Kafka / event bus / microservices / external policy server.
- No RLS migration changes.
- No new policy DSL.
- No PO database bypass.

## 8. Deliverables

A. Code changes (every modified file + why)
B. Casbin model (final matcher + how ABAC attributes are evaluated)
C. Platform Owner behavior (how bypass was removed, what now determines access)
D. Multi-role behavior (changed or intentionally unchanged)
E. Policy identification (fixed / deferred / unchanged)
F. Tests (new/modified + purpose)
G. Test results (run / passed / failed / skipped)
H. Architecture impact confirmation (business-agnostic, no ORM imports, no RLS
   bypass, no messaging, no restructuring)