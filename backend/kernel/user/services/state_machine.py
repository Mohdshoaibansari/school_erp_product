"""User lifecycle state machine (Decision 8, AC-10, AC-11).

States: Invited → Pending → Active → Suspended → Archived.
Archived is terminal (no outgoing arcs).

These are pure-data structures — no DB access, no side-effects.
The repos call ``validate_user_transition`` before persisting a state change.
"""

from __future__ import annotations


class InvalidUserTransitionError(ValueError):
    """Raised when a user lifecycle transition is not in the allowed arcs."""

    def __init__(self, old_state: str, new_state: str) -> None:
        self.old_state = old_state
        self.new_state = new_state
        super().__init__(
            f"User lifecycle transition '{old_state}→{new_state}' is not allowed"
        )


# ============================================================
# User lifecycle state machine
# ============================================================

USER_STATES: frozenset[str] = frozenset({
    "invited", "pending", "active", "suspended", "archived",
})

USER_TERMINAL_STATES: frozenset[str] = frozenset({"archived"})

USER_ARCS: dict[str, frozenset[str]] = {
    "invited": frozenset({"pending"}),
    "pending": frozenset({"active"}),
    "active": frozenset({"suspended", "archived"}),
    "suspended": frozenset({"active", "archived"}),
    "archived": frozenset(),  # terminal — no outgoing arcs
}


def validate_user_transition(old_state: str, new_state: str) -> None:
    """Validate a User lifecycle arc.

    Raises ``InvalidUserTransitionError`` if:
    - ``old_state`` or ``new_state`` is not a known state.
    - ``old_state`` is terminal (archived).
    - The arc ``(old_state → new_state)`` is not in ``USER_ARCS``.
    """
    old = old_state.lower()
    new = new_state.lower()
    if old not in USER_STATES:
        raise InvalidUserTransitionError(old_state, new_state)
    if new not in USER_STATES:
        raise InvalidUserTransitionError(old_state, new_state)
    if old in USER_TERMINAL_STATES:
        raise InvalidUserTransitionError(old_state, new_state)
    if new not in USER_ARCS.get(old, frozenset()):
        raise InvalidUserTransitionError(old_state, new_state)


def is_user_state_terminal(state: str) -> bool:
    """Check if a User state is terminal."""
    return state.lower() in USER_TERMINAL_STATES
