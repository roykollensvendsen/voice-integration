"""What the voice layer is allowed to ask for, which is always less than the gateway allows.

Three layers of permission stand between a spoken sentence and a command that
runs. The harness has its own, the gateway has one over that, and this is the
third and narrowest: the set of tools this voice session may call at all, and
the answers it may give to an approval. The voice layer can only ever narrow.
It has no mechanism for widening anything, on purpose, because a channel that
mishears "deny" as "fine" should not be able to grant standing permission.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from voice_bridge.contract import BY_NAME

#: The answers a voice session may give to a pending approval. `session` and
#: `always` are gateway-side answers and belong to a view with a screen.
SPOKEN_APPROVAL_CHOICES: frozenset[str] = frozenset({"once", "deny"})


class Refused(Exception):
    """A call the voice layer is not allowed to make."""


@dataclass(frozen=True)
class Capabilities:
    """The tools one voice session may call."""

    tools: frozenset[str] = field(default_factory=lambda: frozenset(BY_NAME))

    def permit(self, name: str, arguments: dict[str, object]) -> None:
        """Raise `Refused` unless this session may make exactly this call."""
        # RULE: a voice session may only call a tool it was given
        if name not in self.tools:
            message = f"{name} is not in this voice session's capabilities"
            raise Refused(message)
        if name not in BY_NAME:
            message = f"{name} is not a voice tool"
            raise Refused(message)
        if name == "approval_resolve":
            choice = str(arguments.get("choice", ""))
            # RULE: an approval answered by voice binds one call only
            if choice not in SPOKEN_APPROVAL_CHOICES:
                message = (
                    f"{choice!r} would outlive this call; voice may answer "
                    f"{' or '.join(sorted(SPOKEN_APPROVAL_CHOICES))}"
                )
                raise Refused(message)
