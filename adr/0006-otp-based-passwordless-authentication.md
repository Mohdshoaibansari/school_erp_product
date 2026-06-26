# ADR-0006: OTP-based Passwordless Authentication

## Status

Accepted

## Date

2026-06-26

## Context

The School ERP needs passwordless authentication via email OTP for:
- User onboarding (new users without passwords)
- Password recovery (forgot password flow)
- Alternative login method (convenience)

## Decision

Implement OTP-based passwordless authentication with the following design:

1. **OTP Generation**: 6-digit numeric code with configurable expiry (default 10 minutes)
2. **OTP Storage**: Dedicated `otp_records` table with hashed codes (Argon2id)
3. **OTP Delivery**: Email via NotificationService
4. **OTP Verification**: Single-use, max 3 attempts per OTP
5. **Purpose Support**: LOGIN and PASSWORD_RESET

### Key Design Choices

- **Hashed Storage**: OTP codes are hashed before storage (Argon2id) for security
- **Single-Use**: OTP is invalidated after successful verification
- **Attempt Limiting**: Max 3 verification attempts per OTP to prevent brute force
- **Purpose Separation**: OTPs are tagged with purpose (LOGIN vs PASSWORD_RESET)

## Consequences

### Positive

- Users can login without passwords
- Password recovery is secure and user-friendly
- OTP codes are secure (hashed, single-use, attempt-limited)

### Negative

- Depends on email delivery (NotificationService)
- Additional database table for OTP storage
- OTP email may be delayed or filtered as spam

### Risks

- **Email Delivery Delay**: Mitigated by 10-minute expiry; user can request new OTP
- **Brute Force OTP**: Mitigated by 3-attempt limit and rate limiting on OTP requests

## Alternatives Considered

1. **SMS-based OTP**: Rejected due to cost and complexity
2. **Magic Links**: Rejected due to email client compatibility issues
3. **Time-based OTP (TOTP)**: Rejected due to user experience (requires authenticator app)

## Related

- ADR-0004: Single multi-tenant deployment with row-level isolation
- authentication-enhancements change
