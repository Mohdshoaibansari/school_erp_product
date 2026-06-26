## Why

The original kernel-foundation change implemented basic email/password authentication (Tasks 4.1, 4.2) but deferred two critical security features:
- **OTP-based passwordless login** (Task 4.3) — Required for user onboarding and password recovery
- **Rate limiting & account lockout** (Task 4.4) — Required to prevent brute force attacks

These features are essential for production security and user experience.

## What Changes

- Implement OTP (One-Time Password) generation and verification for passwordless email login
- Implement rate limiting with configurable failed attempt thresholds
- Implement account lockout with automatic unlock after configurable duration
- Add email delivery integration for OTP notifications (depends on Notification Service)

## Capabilities

### New Capabilities

- `otp-login`: OTP-based passwordless authentication via email. Covers OTP generation, verification, expiration, and email delivery.
- `rate-limiting`: Account protection against brute force attacks. Covers failed attempt tracking, account lockout, lockout duration, and automatic unlock.

### Modified Capabilities

- `authentication`: Extends existing email/password auth with OTP login option and rate limiting enforcement.

## Impact

- **Packages affected**: `packages/kernel/src/auth/`
- **Dependencies**: Notification Service (for OTP email delivery), Config Service (for rate limit thresholds)
- **Database**: New tables for OTP storage, rate limit tracking
- **API**: New endpoints for OTP request/verify, rate limit status
