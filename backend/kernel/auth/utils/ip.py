"""IP address extraction utility (D31, AC-28).

Reads X-Forwarded-For header (first IP if multiple) or falls back to request's direct IP.
Used for populating login_attempt.ip_address.
"""

from __future__ import annotations

from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """Extract the real client IP from the request.

    Reads X-Forwarded-For header (first IP if multiple proxies).
    Falls back to request.client.host if no header present.

    Args:
        request: the FastAPI request object.

    Returns:
        The client IP address string, or None if unavailable.
    """
    # Check X-Forwarded-For header first (set by load balancers/proxies)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For format: "client, proxy1, proxy2"
        # Take the first IP (the real client)
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    # Fall back to direct connection IP
    if request.client:
        return request.client.host

    return None
