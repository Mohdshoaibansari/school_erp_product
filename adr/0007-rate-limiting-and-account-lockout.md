# ADR-0007: Rate Limiting and Account Lockout

## Status

Accepted

## Date

2026-06-26

## Context

The School ERP needs protection against brute force attacks on authentication endpoints:
- Email/password login attempts
- OTP verification attempts
- Password reset attempts

## Decision

Implement rate limiting and account lockout with the following design:

1. **Tracking**: Login attempts tracked in `login_attempts` table (email, IP, success, timestamp)
2. **Lockout**: Per-account lockout after configurable failed attempts (default: 5)
3. **Duration**: Configurable lockout duration (default: 15 minutes)
4. **Unlock**: Automatic unlock after duration expires; manual unlock by administrators
5. **Configuration**: Thresholds stored in ConfigService per institution

### Key Design Choices

- **Per-Account Lockout**: Lockout is per-user account, not per-IP address
- **Derived Count**: Failed attempt count derived from recent attempts, not a counter field on User
- **Automatic Unlock**: No background job needed; unlock via timestamp comparison
- **ConfigService Integration**: Thresholds configurable per institution via ConfigService

## Consequences

### Positive

- Protects against brute force attacks
- Configurable thresholds per institution
- No background jobs for lockout management
- Administrators can manually unlock accounts

### Negative

- Legitimate users may be locked out during attacks
- Requires ConfigService integration
- Additional database table for attempt tracking

### Risks

- **Account Lockout DoS**: Mitigated by admin manual unlock and short lockout duration (15 min)
- **Config Not Set**: Mitigated by sensible defaults (5 attempts, 15 min lockout)

## Alternatives Considered

1. **IP-based Rate Limiting**: Rejected due to NAT/proxy issues (multiple users behind same IP)
2. **CAPTCHA Integration**: Rejected due to user experience concerns; can add later
3. **Progressive Delays**: Rejected due to complexity; lockout is simpler and more effective

## Related

- ADR-0004: Single multi-tenant deployment with row-level isolation
- authentication-enhancements change
