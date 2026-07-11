"""C-02 Identity & User Management — Casbin policies (A5, AC-16).

C-04 owns the Casbin framework; C-02 supplies the user/role content.
Currently a no-op — C-04 will invoke the register_policies hook at startup.
"""

from __future__ import annotations

from typing import Any


def register_policies(enforcer: Any) -> None:
    """Register C-02 Casbin policies on the given enforcer (A5).

    Currently a no-op. C-04 will provide the enforcer and invoke this hook.
    C-02's policies will define what roles (Teacher, HOD, Principal, etc.)
    can do with user-related resources.
    """
    # No-op until C-04 is built.
    pass
