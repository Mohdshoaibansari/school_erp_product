"""C-03 Authentication — kernel module for identity verification (A2).

Single gateway for all users across all clients. No module implements
its own login. C-03 owns: AuthenticationMethod (Phase 2), IdentityProvider
(Phase 2), Session (Supabase-managed), LoginAttempt, MfaConfig (Phase 2).
"""
