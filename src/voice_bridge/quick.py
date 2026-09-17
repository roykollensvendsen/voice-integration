"""The handful of things the bridge answers itself, without waking the gateway.

Every request went to the gateway, which carries thirty-three thousand tokens
of its own preamble before it reads a word of the question. Twelve seconds to
be told the time. The gateway is worth that when an agent has to run; it is
absurd when the answer is already in this process, or one HTTP call away.

Five kinds of question stop here. Three the bridge simply knows — the clock, the
ledger it writes, the run it is following. Two it fetches: where the person is,
and what the web says. Everything else travels, which is the point: this is a
short list on purpose, and adding to it is a decision. ADR-VI-022.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from voice_bridge.server import Bridge

#: Longer than this and it is not one of the questions the bridge simply knows,
#: whatever words it happens to contain. "What time did you start the run that
#: broke the tests" is a question for the gateway.
SHORTEST_IS_SAFEST = 60

CLOCK = ("hva er klokka", "hva er klokken", "klokka", "klokken", "what time", "the time")
SPENT = ("hvor mye har jeg brukt", "hvor mye er igjen", "budsjett", "how much is left", "budget")
RUNNING = ("hva kjører", "hva jobber du med", "hva skjer nå", "what is running", "what are you doing")
PLACE = ("hvor er jeg", "hvor befinner jeg", "where am i", "my location", "hvilket sted er jeg")

#: What marks a question as one for the web rather than for this machine. The
#: gateway is the one that reads files and runs things; the web is everything
#: that is simply known somewhere else.
LOOK_IT_UP = (
    "søk opp",
    "slå opp",
    "google",
    "på nettet",
    "hva sier nyhetene",
    "siste nytt",
    "hvem vant",
    "hva koster",
    "når er",
    "hvem er",
    "hva er prisen",
    "look up",
    "search for",
    "on the web",
    "who won",
    "latest news",
)

#: The web answer is read aloud, so it loses its footnotes. A spoken URL is
#: noise, and this model writes them inline as markdown links.
CITATION = re.compile(r"\s*\(\[[^\]]*\]\([^)]*\)\)|\s*\[[^\]]*\]\((?:https?|www)[^)]*\)")

SEARCH_URL = "https://api.openai.com/v1/responses"
SEARCH_MODEL = "gpt-5-mini"
SEARCH_SECONDS = 25.0

PLACES_URL = "https://nominatim.openstreetmap.org/reverse"
PLACES_SECONDS = 8.0
#: Nominatim asks every caller to say who they are, and refuses the ones that do not.
POLITE = "voice-integration (github.com/roykollensvendsen/voice-integration)"


def _matches(said: str, words: tuple[str, ...]) -> bool:
    return any(word in said for word in words)


def place_of(latitude: float, longitude: float) -> str | None:
    """The name of a place, from coordinates nobody can say out loud."""
    query = urllib.parse.urlencode({"lat": latitude, "lon": longitude, "format": "jsonv2", "zoom": 14})
    request = urllib.request.Request(  # noqa: S310 — a constant HTTPS URL
        f"{PLACES_URL}?{query}",
        headers={"User-Agent": POLITE},
    )
    try:
        with urllib.request.urlopen(request, timeout=PLACES_SECONDS) as reply:  # noqa: S310 — as above
            found = json.loads(reply.read() or b"{}").get("address") or {}
    except (OSError, json.JSONDecodeError):
        return None
    near = found.get("city") or found.get("town") or found.get("village") or found.get("municipality")
    return ", ".join(part for part in (found.get("suburb"), near, found.get("country")) if part) or None


def on_the_web(question: str, key: str | None = None) -> str | None:
    """What the web says, in one sentence, or None when it could not be asked."""
    token = key if key is not None else os.environ.get("OPENAI_API_KEY", "")
    if not token:
        return None
    body = json.dumps(
        {
            "model": SEARCH_MODEL,
            "tools": [{"type": "web_search"}],
            # `minimal` is refused outright with this tool, and the answer needs
            # room after the search: a small cap is spent on reasoning and the
            # reply never gets written.
            "reasoning": {"effort": "low"},
            "max_output_tokens": 2000,
            "input": f"{question}\n\nSvar med én kort setning som kan leses høyt. Ingen lenker.",
        }
    )
    request = urllib.request.Request(
        SEARCH_URL,
        data=body.encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=SEARCH_SECONDS) as reply:  # noqa: S310 — as above
            answered = json.loads(reply.read() or b"{}")
    except (urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return None
    for part in answered.get("output") or []:
        for piece in part.get("content") or []:
            if piece.get("type") == "output_text":
                return CITATION.sub("", str(piece.get("text", ""))).strip() or None
    return None


def _known(bridge: Bridge, said: str) -> str | None:
    """The three the bridge simply knows, plus the one it was told."""
    if _matches(said, CLOCK):
        return f"Klokka er {dt.datetime.now().astimezone():%H:%M}."
    if _matches(said, SPENT):
        left = bridge.ledger.remaining_usd()
        minutes = bridge.ledger.remaining_minutes()
        return f"Du har {left:.2f} dollar igjen denne måneden, omtrent {minutes} minutter."
    if _matches(said, RUNNING):
        return "Ingenting kjører akkurat nå." if bridge.following is None else "Noe kjører fortsatt."
    if _matches(said, PLACE):
        return f"Du er i {bridge.placed}." if bridge.placed else "Jeg vet ikke hvor du er."
    return None


def answer(bridge: Bridge, transcript: str) -> str | None:
    """What the bridge can say itself, or None when this belongs to the gateway."""
    said = transcript.strip().casefold()
    if _matches(said, LOOK_IT_UP):
        # RULE: a question for the web is asked of the web, not of an agent
        return on_the_web(transcript.strip())
    # RULE: only a short question is ever answered without the gateway
    if len(said) > SHORTEST_IS_SAFEST:
        return None
    return _known(bridge, said)
