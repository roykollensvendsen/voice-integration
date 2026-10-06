"""Who a turn goes to: the voice alone, the gateway, or one Claude Code session.

The person chooses, by tapping a tree on the page or by saying so, and the
choice stays until they change it. The reason is theirs, in two words: cost and
response. The voice alone is free and instant; the gateway is a model call of
about ten seconds; one session is about five seconds on the subscription.
ADR-VI-026.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
from dataclasses import dataclass
from typing import Any

#: The three kinds of target there are.
KINDS = ("voice", "hermes", "session")

#: Longer than this and "talk to" is part of a sentence about something else.
SHORTEST_IS_SAFEST = 60

_TALK_TO = r"^(?:snakk|prat|talk|speak)\s+(?:med|to|with)\s+(?:the\s+)?"
_TO_VOICE = re.compile(_TALK_TO + r"(?:stemmen|stemmelaget|voice|deg|you)$")
_TO_HERMES = re.compile(_TALK_TO + r"hermes$")
_TO_SESSION = re.compile(_TALK_TO + r"(?:økta\s+|økten\s+|session\s+)?(.+?)(?:\s+(?:økta|økten|session))?$")


@dataclass(frozen=True)
class Target:
    """Where a turn the bridge cannot answer itself is sent."""

    kind: str
    name: str = ""

    def said(self) -> str:
        """Who this is, in words a person hears."""
        if self.kind == "voice":
            return "the voice alone"
        if self.kind == "hermes":
            return "Hermes"
        return self.name

    def as_json(self) -> dict[str, str]:
        """The shape the page and the state file take."""
        return {"kind": self.kind, "name": self.name} if self.kind == "session" else {"kind": self.kind}


def state_file() -> pathlib.Path:
    """Where `voicebridge serve` keeps the choice between runs."""
    base = os.environ.get("XDG_STATE_HOME") or str(pathlib.Path.home() / ".local" / "state")
    return pathlib.Path(base) / "voice-bridge" / "target.json"


def load(path: pathlib.Path | None) -> Target:
    """The choice made last time, or the gateway when there was none."""
    if path is None:
        return Target("hermes")
    try:
        kept = json.loads(path.read_text())
    except (OSError, ValueError):
        return Target("hermes")
    kind = str(kept.get("kind", "")) if isinstance(kept, dict) else ""
    if kind not in KINDS or (kind == "session" and not kept.get("name")):
        return Target("hermes")
    return Target(kind, str(kept.get("name", "")) if kind == "session" else "")


def save(path: pathlib.Path | None, chosen: Target) -> None:
    """Keep the choice where a restart will find it."""
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chosen.as_json()))


def switch_request(said: str) -> Target | str | None:
    """A target, a session name still to be matched, or None when this was not a switch."""
    words = said.strip().strip(".!?,").casefold()
    words = re.sub(r"^(?:jeg vil |i want to |can we |kan vi |la oss )", "", words)
    # RULE: a long sentence that mentions talking to someone is not a switch
    if len(words) > SHORTEST_IS_SAFEST:
        return None
    if _TO_VOICE.match(words):
        return Target("voice")
    if _TO_HERMES.match(words):
        return Target("hermes")
    found = _TO_SESSION.match(words)
    return found.group(1).strip() if found else None


def matching(asked: str, running: list[dict[str, Any]]) -> list[str]:
    """The running sessions a spoken name or project could mean."""
    wanted = asked.casefold().replace(" ", "")
    exact = [s["name"] for s in running if str(s.get("name", "")).casefold().replace(" ", "") == wanted]
    if exact:
        return exact
    return [
        str(s["name"])
        for s in running
        if wanted in str(s.get("name", "")).casefold().replace(" ", "")
        or wanted in str(s.get("project", "")).casefold().rsplit("/", 1)[-1].replace(" ", "")
    ]
