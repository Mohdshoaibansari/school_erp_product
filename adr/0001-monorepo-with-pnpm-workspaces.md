# ADR-0001: Monorepo with pnpm workspaces

## Status

Accepted

## Context

The School ERP system comprises multiple bounded contexts (tenant, identity, academic, attendance, fees, etc.) that must be developed as separate packages to enforce domain boundaries. A solo developer is building the system initially, so separate repositories with versioning and publishing overhead would slow iteration. The packages must share code (kernel services consumed by business modules) but remain independently testable and deployable.

## Decision

Use a single monorepo managed by pnpm workspaces. Packages live under `packages/` with namespace `@school-erp/*`. The API server lives under `apps/api`. pnpm workspace protocol allows `@school-erp/attendance` to import `@school-erp/kernel` as if published, resolving to source on disk.

## Consequences

- **Easier**: A single PR can modify kernel and a consuming module simultaneously. No version bumping or publishing during development. Shared linting, TypeScript config, and testing in one place.
- **Harder**: Repository grows large as modules are added. CI must be configured to run tests only for affected packages. Splitting to separate repos later requires extracting shared config and setting up a private package registry.
- **Mitigation**: If team grows beyond 3 developers or packages exceed 20, evaluate splitting to a multi-repo setup.
