## Context

The School ERP requires enhanced authentication security beyond basic email/password login. The original kernel-foundation change implemented Tasks 4.1 (Argon2id) and 4.2 (JWT) but deferred:
- Task 4.3: OTP-based passwordless login
- Task 4.4: Rate limiting and account lockout

These are critical for production security and user onboarding.

## Goals / Non-Goals

**Goals:**
- Implement OTP-based passwordless login via email
- Implement rate limiting with configurable thresholds
- Implement account lockout with automatic unlock
- Integrate with ConfigService for threshold configuration
- Integrate with NotificationService for OTP email delivery

**Non-Goals:**
- SMS-based OTP (future enhancement)
- Multi-factor authentication (future enhancement)
- IP-based rate limiting (per-account only for now)
- CAPTCHA integration (future enhancement)

## Decisions

### Decision 1: OTP Storage

OTP records stored in dedicated `otp_records` table with:
- `code`: 6-digit numeric code
- `email`: Target email address
- `purpose`: LOGIN or PASSWORD_RESET
- `expiresAt`: Expiration timestamp
- `usedAt`: Usage timestamp (null if unused)
- `attempts`: Number of verification attempts

OTP codes are hashed before storage (Argon2id) for security.

### Decision 2: Rate Limiting Storage

Login attempts tracked in `login_attempts` table with:
- `email`: User email
- `ipAddress`: Client IP (for logging only, not blocking)
- `success`: Boolean
- `timestamp`: When the attempt occurred

Failed attempt count derived from recent attempts, not a counter field on User.

### Decision 3: Lockout Strategy

- Lockout is per-account, not per-IP
- Lockout duration configurable via ConfigService
- Automatic unlock via timestamp comparison (no background job needed)
- Manual unlock available for administrators

### Decision 4: Config Integration

Rate limiting thresholds stored in ConfigService:
- `auth.max_failed_attempts`: Default 5
- `auth.lockout_duration_minutes`: Default 15
- `auth.otp_max_attempts`: Default 3
- `auth.otp_expiry_minutes`: Default 10

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AuthService                              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Login         │  │ OTP          │  │ Rate Limit   │      │
│  │ (existing)    │  │ Request      │  │ Check        │      │
│  │               │  │ Verify       │  │ Record       │      │
│  │               │  │              │  │ Lockout      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                 │                │
│         ▼                 ▼                 ▼                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   PrismaClient                        │  │
│  │  users | otp_records | login_attempts                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ ConfigService │  │ Notification │                        │
│  │ (thresholds)  │  │ Service      │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| OTP email delivery delays | OTP expiry set to 10 minutes; user can request new OTP |
| Brute force OTP | Max 3 verification attempts per OTP; rate limiting on OTP requests |
| Account lockout DoS | Admin manual unlock; lockout duration is short (15 min default) |
| Config not set | Sensible defaults for all rate limiting parameters |
