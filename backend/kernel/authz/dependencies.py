"""C-04 Authorization — FastAPI dependencies (D10, AC-11).

Provides:
- ``get_enforcer()`` — the global Casbin enforcer singleton.
"""

from __future__ import annotations

from typing import Any

_enforcer: Any = None


def set_enforcer(enforcer: Any) -> None:
    """Store the global Casbin enforcer singleton (called by app factory)."""
    global _enforcer
    _enforcer = enforcer


def get_enforcer() -> Any:
    """Return the global Casbin enforcer singleton (D10, 5.2).

    Injected via ``Depends(get_enforcer)``. Returns the instance set by the
    app factory during ``create_app()``.
    """
    return _enforcer
