"""Lifecycle state machines for Client (D8) and Institution (D9).

Defines the allowed transition arcs as directed graphs. A ``transition``
function validates an arc and raises ``InvalidTransitionError`` on disallowed
moves. ``Terminated`` is terminal for Clients (no outgoing arcs). Institutions
have no ``Terminated`` state (D9).

These are pure-data structures — no DB access, no side-effects. The repos
and ``services/lifecycle.py`` call ``validate_transition`` before persisting
a state change.
"""

from __future__ import annotations


class InvalidTransitionError(ValueError):
    """Raised when a lifecycle transition is not in the allowed arcs."""

    def __init__(self, entity_type: str, old_state: str, new_state: str) -> None:
        self.entity_type = entity_type
        self.old_state = old_state
        self.new_state = new_state
        super().__init__(
            f"{entity_type} lifecycle transition '{old_state}→{new_state}' is not allowed"
        )


# ============================================================
# D8 — Client lifecycle state machine
# ============================================================
# States: prospective, active, suspended, archived, terminated
# Terminated is terminal (no outgoing arcs).
# Archived is the only re-activatable inactive state (Archived→Active).

CLIENT_STATES: frozenset[str] = frozenset({
    "prospective", "active", "suspended", "archived", "terminated",
})

CLIENT_TERMINAL_STATES: frozenset[str] = frozenset({"terminated"})

CLIENT_ARCS: dict[str, frozenset[str]] = {
    "prospective": frozenset({"active", "archived"}),
    "active": frozenset({"suspended", "archived", "terminated"}),
    "suspended": frozenset({"active", "archived", "terminated"}),
    "archived": frozenset({"active", "terminated"}),
    "terminated": frozenset(),  # terminal — no outgoing arcs
}


# ============================================================
# D9 — Institution lifecycle state machine
# ============================================================
# States: onboarding, active, inactive, archived — NO terminated.
# Archived→Active is the re-activation arc.

INSTITUTION_STATES: frozenset[str] = frozenset({
    "onboarding", "active", "inactive", "archived",
})

INSTITUTION_TERMINAL_STATES: frozenset[str] = frozenset()  # no terminal state

INSTITUTION_ARCS: dict[str, frozenset[str]] = {
    "onboarding": frozenset({"active", "archived"}),
    "active": frozenset({"inactive", "archived"}),
    "inactive": frozenset({"active", "archived"}),
    "archived": frozenset({"active"}),
}


# ============================================================
# Validation functions
# ============================================================

def validate_client_transition(old_state: str, new_state: str) -> None:
    """Validate a Client lifecycle arc (D8).

    Raises ``InvalidTransitionError`` if:
    - ``old_state`` or ``new_state`` is not a known state.
    - ``old_state`` is terminal (terminated).
    - The arc ``(old_state → new_state)`` is not in ``CLIENT_ARCS``.
    """
    old = old_state.lower()
    new = new_state.lower()
    if old not in CLIENT_STATES:
        raise InvalidTransitionError("Client", old_state, new_state)
    if new not in CLIENT_STATES:
        raise InvalidTransitionError("Client", old_state, new_state)
    if old in CLIENT_TERMINAL_STATES:
        raise InvalidTransitionError("Client", old_state, new_state)
    if new not in CLIENT_ARCS.get(old, frozenset()):
        raise InvalidTransitionError("Client", old_state, new_state)


def validate_institution_transition(old_state: str, new_state: str) -> None:
    """Validate an Institution lifecycle arc (D9).

    Raises ``InvalidTransitionError`` if:
    - ``old_state`` or ``new_state`` is not a known state.
    - ``new_state`` is ``terminated`` (institutions have no Terminated — D9).
    - The arc ``(old_state → new_state)`` is not in ``INSTITUTION_ARCS``.
    """
    old = old_state.lower()
    new = new_state.lower()
    if new == "terminated":
        raise InvalidTransitionError("Institution", old_state, new_state)
    if old not in INSTITUTION_STATES:
        raise InvalidTransitionError("Institution", old_state, new_state)
    if new not in INSTITUTION_STATES:
        raise InvalidTransitionError("Institution", old_state, new_state)
    if new not in INSTITUTION_ARCS.get(old, frozenset()):
        raise InvalidTransitionError("Institution", old_state, new_state)


def is_client_state_terminal(state: str) -> bool:
    """Check if a Client state is terminal (D8)."""
    return state.lower() in CLIENT_TERMINAL_STATES


def is_institution_operationally_active(
    institution_status: str, client_status: str,
) -> bool:
    """Compute the **effective** operational state at runtime (D9, AC-7).

    An Institution is operationally Active ONLY if:
    - its own ``current_lifecycle_status`` is ``active``, AND
    - its Client's ``current_lifecycle_status`` is ``active``.

    This is a **runtime** computation — it does NOT mutate any persisted
    state. When a Client is suspended, the Institution's row is untouched;
    this function simply returns ``False``, gating access. When the Client
    is restored to ``active``, this function returns ``True`` again without
    any persisted state restoration (AC-7).
    """
    return (
        institution_status.lower() == "active"
        and client_status.lower() == "active"
    )
