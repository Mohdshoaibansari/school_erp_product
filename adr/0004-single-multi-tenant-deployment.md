# 0004. Single multi-tenant deployment with row-level isolation

- Status: accepted
- Date: 2026-06-20

## Context

The platform must serve multiple clients while maintaining data isolation. Three approaches: per-client instances (dedicated app + DB per client), single multi-tenant app with schema-per-tenant, or single multi-tenant app with row-level tenancy. Per-client instances offer maximum isolation but maximum operational cost. Schema-per-tenant offers good isolation with shared app but complex migrations. Row-level tenancy offers simplest operations but weakest isolation.

## Decision

Use a single multi-tenant deployment with row-level tenancy (tenant_id on every table). One app server, one PostgreSQL cluster. If a client demands physical isolation, deploy a dedicated instance manually on request. Self-host is deferred entirely — not a product feature.

## Consequences

- Positive: Simplest operations — one deploy, one DB cluster, one monitoring surface
- Positive: Single codebase, no branch management
- Neutral: If a client demands physical isolation, must deploy a new instance manually
- Negative: Row-level isolation depends on application correctness — a tenant_id filter bug could leak data
