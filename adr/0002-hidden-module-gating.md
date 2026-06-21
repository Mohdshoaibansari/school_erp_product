# 0002. Hidden module gating

- Status: accepted
- Date: 2026-06-20

## Context

Free-tier users should not access paid modules (Exams, Homework, Transport, etc.). Two approaches: upsell gating (show locked modules with upgrade prompts) and hidden gating (paid modules are invisible). Upsell gating is common but creates a "freemium" feel and constant reminder of what the user doesn't have. Hidden gating makes the free product feel complete.

## Decision

Paid modules are completely invisible to free-tier users. No lock icons, no disabled menu items, no upgrade banners in the app. The navigation menu shows only free modules. Direct URL access to paid module routes returns 404. API access to paid module endpoints returns 403 without revealing the module name. Module availability is driven by subscription data, not hardcoded per tenant.

## Consequences

- Positive: Clean, complete product experience for free-tier users
- Positive: No in-app friction or feature shaming
- Negative: Missed in-app conversion opportunities — upgrade path must be driven via email, sales, or out-of-band channels
- Negative: New module additions require no frontend deployment, but existing free users won't know about them
