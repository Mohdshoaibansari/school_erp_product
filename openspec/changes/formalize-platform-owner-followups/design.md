# Design — Formalize Platform Owner Followups

## Context

This is a **documentation-only change**. All 7 items being formalized are already implemented and live on `main` — they were added during manual E2E testing of the `add-platform-owner-separation` change to fix gaps and bugs.

The corresponding evidence lives in:
- `openspec/changes/archive/2026-07-29-add-platform-owner-separation/verify.md` — "Additional Changes Made Outside Spec" section
- Git history: commits `85a17e1`, `825793a`, `9fa4da0` (in current branch's history)

## Goals / Non-Goals

**Goals:**
- Create one self-contained spec (`specs/platform-owner-followups/spec.md`) describing all 7 formalizations as 3 grouped requirements
- Make future reviewers able to search the spec and find current behavior
- Make verification straightforward (one change, one set of scenarios)

**Non-Goals:**
- No code changes
- No spec splits across multiple capability files (consolidated in one for reviewability)
- No behavior changes

## Decisions

### D1: One new spec, not deltas into existing specs

**Rationale:** All 7 items emerged from a single testing cycle on a single feature (platform owner separation). Keeping them in one spec:
- Makes the "followup" nature obvious
- Simplifies verification (one verify.md for one set of behaviors)
- Preserves auditability (one change, one archive entry)

**Alternative considered:** Distribute to each capability's natural spec (auth, identity, authorization, homework). Rejected because it would scatter the provenance and make future readers unable to find the "why" behind these changes.

### D2: ADDED Requirements, not bug-fix notes

**Rationale:** Per grill-me Q3. Future readers see clean requirements, not "this was a bug" notes. The provenance lives in `verify.md` and git history.

### D3: 3 grouped requirements, not 7 individual

**Rationale:** Per grill-me Q5.
- `Middleware role resolution` (items 1, 5) — same module, related concern
- `Cross-cutting refactors` (items 4, 6, 7) — orthogonal to user-facing behavior
- `Client Director lifecycle support` (items 2, 3) — new concept, big picture

## Risks / Trade-offs

- [Spec is non-canonical home] → A future maintainer searching "where is client_director role defined" will find it here, not in C-04 authorization spec. Mitigated by cross-referencing C-04 in the requirement.
- [No code changes to validate] → Verification relies on existing tests + manual E2E evidence. Mitigated by linking the verify.md to the previous change's evidence.

## Migration Plan

- No code deployment needed
- This change only updates `openspec/changes/.../specs/` (and creates verify.md)
- After archive, the new spec lives in `openspec/specs/platform-owner-followups/spec.md`

## Open Questions

- None — all 7 items are well-understood from the previous verify.md.
