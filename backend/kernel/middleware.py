"""Subdomain + Supabase JWT middleware (A6, task 7.1).

Reads the ``Host`` header, extracts the subdomain, resolves the Client (by
slug = subdomain per D3), validates the Supabase JWT (python-jose; tests mint
a JWT with a test secret), and SETS the contextvar with ``client_id`` + claims.

Platform-scoped requests (``/api/v1/platform/...``) set ``is_platform_owner=True``
per D11. Endpoints use ``Depends(get_tenant_context)`` — never touch the
contextvar directly (A6 invariant).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from jose import jwk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from kernel.tenant_context import TenantContext, set_tenant_context

logger = logging.getLogger(__name__)

# Test JWT secret — in production this is the Supabase project's JWT secret.
# C-01 CONSUMES JWTs; it does not issue them (tech-stack ADR §3).
JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "test-secret-for-c01")
JWT_ALGORITHM = "HS256"

# Paths that are platform-scoped (Platform-Owner-only per D11)
_PLATFORM_PREFIX = "/api/v1/platform/"

# Reserved subdomain labels that map to "platform" (no specific client)
_PLATFORM_HOSTS = frozenset({"localhost", "127.0.0.1", "platform", "api", "admin", ""})


_SUPABASE_JWKS_URL = os.environ.get("SUPABASE_URL", "") + "/auth/v1/.well-known/jwks.json" if os.environ.get("SUPABASE_URL") else None
_jwks_cache: dict | None = None


def _verify_jwt(token: str) -> dict:
    """Verify a Supabase JWT — handles HS256 (local) and ES256 (cloud)."""
    global _jwks_cache
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        pass
    if _SUPABASE_JWKS_URL:
        if _jwks_cache is None:
            try:
                from urllib.request import urlopen
                import json
                resp = urlopen(_SUPABASE_JWKS_URL)
                _jwks_cache = json.loads(resp.read())
            except Exception:
                pass
        if _jwks_cache:
            try:
                header = jwt.get_unverified_header(token)
                kid = header.get("kid")
                alg = header.get("alg", "RS256")
                key_data = None
                for k in _jwks_cache.get("keys", []):
                    if k.get("kid") == kid:
                        key_data = k
                        break
                if key_data:
                    public_key = jwk.construct(key_data)
                    return jwt.decode(token, public_key, algorithms=[alg], audience="authenticated")
            except Exception:
                pass
    raise JWTError("Could not verify JWT")


def mint_test_jwt(
    *,
    user_id: str = "test-user",
    client_id: str | None = None,
    institution_id: str | None = None,
    is_platform_owner: bool = False,
    roles: list[str] | None = None,
    secret: str = JWT_SECRET,
    expires_minutes: int = 60,
) -> str:
    """Mint a Supabase-compatible JWT for testing (tech-stack ADR §3).

    Tests use this — C-01 does not issue JWTs in production (C-03 owns issuance).
    """
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        "iat": datetime.now(timezone.utc),
    }
    if client_id:
        payload["client_id"] = client_id
    if institution_id:
        payload["institution_id"] = institution_id
    payload["is_platform_owner"] = is_platform_owner
    payload["roles"] = roles or []
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def _extract_subdomain(host: str) -> str | None:
    """Extract the client slug subdomain from a Host header (D3).

    ``school-a.localhost:54321`` → ``school-a``
    ``school-a.app.example.com`` → ``school-a``
    ``localhost:54321`` → ``None`` (platform)
    ``127.0.0.1:54321`` → ``None`` (platform)
    """
    # Strip port
    host = host.split(":")[0]
    if host in _PLATFORM_HOSTS:
        return None
    # Split by dots — first segment is the subdomain
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[0]
    return None


def _resolve_client_from_subdomain(subdomain: str) -> uuid.UUID | None:
    """Resolve a Client ID from the subdomain slug (D3).

    This is a lightweight DB lookup — in production, a cache layer would
    sit in front. For tests, this uses a direct SQLAlchemy session.
    """
    from sqlalchemy import create_engine, text
    import os

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
    )
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            # Set platform owner context so RLS allows seeing all clients
            # This is an infrastructure lookup, not a user-facing query
            conn.execute(text("SET LOCAL app.is_platform_owner = 'true'"))
            result = conn.execute(
                text("SELECT id FROM client WHERE slug = :slug"),
                {"slug": subdomain},
            )
            row = result.fetchone()
            return row[0] if row else None
    finally:
        engine.dispose()


class SubdomainJWTMiddleware(BaseHTTPMiddleware):
    """Subdomain → Client resolution + Supabase JWT middleware (A6, 7.1).

    Sets the contextvar with ``client_id`` + claims. Endpoints read
    ``TenantContext`` via ``Depends(get_tenant_context)``.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip non-API paths (health, docs, etc.)
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        host = request.headers.get("host", "")
        subdomain = _extract_subdomain(host)
        is_platform_path = path.startswith(_PLATFORM_PREFIX)
        is_auth_path = path.startswith("/api/auth/")

        logger.debug("[MW] %s %s | host=%s subdomain=%s platform=%s auth=%s",
                      request.method, path, host, subdomain, is_platform_path, is_auth_path)

        # Extract JWT from Authorization header
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # Parse JWT claims
        user_id = None
        jwt_client_id = None
        jwt_institution_id = None
        is_platform_owner = False
        roles: list[str] = []

        if token:
            try:
                # First try to decode as invite JWT (different secret, D6)
                from kernel.auth.services.invite_token import (
                    INVITE_JWT_SECRET,
                    INVITE_JWT_ALGORITHM,
                    INVITE_JWT_ISSUER,
                )
                try:
                    invite_payload = jwt.decode(
                        token,
                        INVITE_JWT_SECRET,
                        algorithms=[INVITE_JWT_ALGORITHM],
                        options={"verify_exp": False},
                    )
                    if invite_payload.get("iss") == INVITE_JWT_ISSUER:
                        # This is an invite JWT — set subdomain-only context (D25)
                        # Don't set user_id from invite JWT
                        logger.debug("[MW] Invite JWT detected (iss=%s) — subdomain-only context", invite_payload.get('iss'))
                        pass
                    else:
                        payload = _verify_jwt(token)
                        user_id = payload.get("sub")
                        jwt_client_id = payload.get("client_id")
                        jwt_institution_id = payload.get("institution_id")
                        is_platform_owner = payload.get("is_platform_owner", False)
                        roles = payload.get("roles", [])
                        logger.debug("[MW] Supabase JWT decoded: user_id=%s roles=%s", user_id, roles)
                except JWTError:
                    payload = _verify_jwt(token)
                    user_id = payload.get("sub")
                    jwt_client_id = payload.get("client_id")
                    jwt_institution_id = payload.get("institution_id")
                    is_platform_owner = payload.get("is_platform_owner", False)
                    roles = payload.get("roles", [])
                    logger.debug("[MW] Supabase JWT decoded (fallback): user_id=%s roles=%s", user_id, roles)
            except JWTError:
                # For auth routes, tolerate invalid JWT — set subdomain-only context (D25)
                # For non-auth routes, reject with 401
                if is_auth_path:
                    # Auth route with invalid JWT — continue with subdomain-only context
                    pass
                else:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or expired JWT"},
                    )

        # Determine client_id:
        # - Platform-scoped path → Platform Owner (no specific client)
        # - Subdomain-resolved → resolve Client from subdomain (D3)
        # - JWT carries client_id as fallback
        # - Auth routes without JWT → subdomain-only context (D25)
        import uuid

        client_id = None
        if is_platform_path:
            is_platform_owner = True
            logger.debug("[MW] Platform path detected — is_platform_owner=True")
        elif subdomain:
            resolved = _resolve_client_from_subdomain(subdomain)
            if resolved:
                client_id = resolved
                logger.debug("[MW] Subdomain '%s' resolved to client_id=%s", subdomain, client_id)
            elif jwt_client_id:
                client_id = uuid.UUID(jwt_client_id) if jwt_client_id else None
                logger.debug("[MW] Subdomain not resolved — using JWT client_id=%s", client_id)
        elif jwt_client_id:
            client_id = uuid.UUID(jwt_client_id) if jwt_client_id else None
            logger.debug("[MW] No subdomain — using JWT client_id=%s", client_id)

        institution_id = None
        if jwt_institution_id:
            institution_id = uuid.UUID(jwt_institution_id)

        # For auth routes without JWT, set subdomain-only context (D25)
        # This allows auth endpoints to read client_id from TenantContext
        if is_auth_path and not user_id and not is_platform_path:
            # Auth route without JWT — set subdomain-only context
            # client_id is already resolved from subdomain above
            pass

        # If roles are empty but we have a user_id, look up roles from DB (D7)
        if user_id and not roles and client_id:
            try:
                from sqlalchemy import create_engine, text as sa_text
                db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
                engine = create_engine(db_url)
                with engine.connect() as conn:
                    conn.execute(sa_text("SET LOCAL app.is_platform_owner = 'true'"))
                    result = conn.execute(sa_text(
                        "SELECT r.name FROM role r "
                        "JOIN role_assignment ra ON r.id = ra.role_id "
                        "WHERE ra.user_id = :uid"
                    ), {"uid": user_id}).fetchall()
                    roles = [row[0] for row in result]
                    if "platform_owner" in roles:
                        is_platform_owner = True
                    logger.debug("[MW] Role lookup from DB: user_id=%s roles=%s is_platform_owner=%s", user_id, roles, is_platform_owner)
                engine.dispose()
            except Exception as e:
                logger.warning("[MW] Role lookup failed: %s", e)
                pass

        ctx = TenantContext(
            client_id=client_id,
            institution_id=institution_id,
            user_id=user_id,
            is_platform_owner=is_platform_owner,
            roles=roles,
        )
        set_tenant_context(ctx)

        logger.info("[MW] Request: %s %s | user=%s client=%s inst=%s roles=%s is_po=%s",
                     request.method, path, user_id, client_id, institution_id, roles, is_platform_owner)

        return await call_next(request)
