"""The handful of things the bridge answers itself, without waking the gateway.

Every request went to the gateway, which carries thirty-three thousand tokens
of its own preamble before it reads a word of the question. Twelve seconds to
be told the time. The gateway is worth that when an agent has to run; it is
absurd when the answer is already in this process.

So a few questions stop here. They are the ones where the bridge is the
authority — the clock, what it has spent, what it is watching — not a guess at
what the gateway would have said. Everything else travels, which is the point:
this is a short list on purpose, and adding to it is a decision.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from voice_bridge.server import Bridge

#: Longer than this and it is not one of these questions, whatever words it
#: happens to contain. "What time did you start the run that broke the tests"
#: is a question for the gateway.
SHORTEST_IS_SAFEST = 60

CLOCK = ("hva er klokka", "hva er klokken", "klokka", "klokken", "what time", "the time")
SPENT = ("hvor mye har jeg brukt", "hvor mye er igjen", "budsjett", "how much is left", "budget")
RUNNING = ("hva kjører", "hva jobber du med", "hva skjer nå", "what is running", "what are you doing")


def _matches(said: str, words: tuple[str, ...]) -> bool:
    return any(word in said for word in words)


def answer(bridge: Bridge, transcript: str) -> str | None:
    """What the bridge can say itself, or None when this belongs to the gateway."""
    said = transcript.strip().casefold()
    # RULE: only a short question is ever answered without the gateway
    if len(said) > SHORTEST_IS_SAFEST:
        return None
    if _matches(said, CLOCK):
        now = dt.datetime.now().astimezone()
        return f"Klokka er {now:%H:%M}."
    if _matches(said, SPENT):
        left = bridge.ledger.remaining_usd()
        minutes = bridge.ledger.remaining_minutes()
        return f"Du har {left:.2f} dollar igjen denne måneden, omtrent {minutes} minutter."
    if _matches(said, RUNNING):
        return "Ingenting kjører akkurat nå." if bridge.following is None else "Noe kjører fortsatt."
    return None
