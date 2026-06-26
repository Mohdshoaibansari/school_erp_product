## 1. OTP Login (Task 4.3)

- [ ] 1.1 Define Prisma model: otp_records with code, email, purpose, expires_at, used_at
- [ ] 1.2 Implement OTP generation: 6-digit code, configurable expiry
- [ ] 1.3 Implement OTP verification: validate code, check expiry, mark as used
- [ ] 1.4 Implement OTP email delivery via Notification Service
- [ ] 1.5 Add OTP request endpoint to AuthService
- [ ] 1.6 Add OTP verify endpoint to AuthService

## 2. Rate Limiting (Task 4.4)

- [ ] 2.1 Define Prisma model: login_attempts with email, ip_address, success, timestamp
- [ ] 2.2 Implement failed attempt tracking in AuthService
- [ ] 2.3 Implement account lockout logic with configurable threshold
- [ ] 2.4 Implement automatic lockout unlock after configurable duration
- [ ] 2.5 Add manual unlock endpoint for administrators
- [ ] 2.6 Integrate rate limiting config with ConfigService

## 3. Integration

- [ ] 3.1 Update login flow to check account lockout before authentication
- [ ] 3.2 Update login flow to record all attempts (success and failure)
- [ ] 3.3 Add rate limiting middleware for auth endpoints
- [ ] 3.4 Write unit tests for OTP and rate limiting
