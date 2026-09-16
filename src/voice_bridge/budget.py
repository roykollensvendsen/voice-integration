"""The month's ceiling, and the refusal that keeps it.

Voice is the only part of this system billed by the second, and it bills while
the microphone is open whether or not anyone is speaking. Everything else runs
on a subscription or a bill this process cannot see. So this is the one place
between an open microphone and a surprise, which is why the ceiling is enforced
rather than noted.

The ledger is a file outside the repository, because what was spent is this
installation's fact and not this project's.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib

from voice_bridge.policy import Refused

#: What a `gpt-live-1` voice session costs, from the model page. Flat, and
#: billed per second, which is what makes a ceiling arithmetic rather than a
#: guess: see ADR-VI-017.
USD_PER_MINUTE = 0.05

#: Chosen by Roy Kollen Svendsen on 2026-09-16, which is the decision
#: ADR-VI-017 recorded the need for and could not make. Twenty dollars is 400
#: minutes, or about thirteen minutes a day.
DEFAULT_CEILING_USD = 20.00


def ceiling_usd() -> float:
    """The ceiling for this installation, which the default is only the start of."""
    return float(os.environ.get("VOICE_BRIDGE_CEILING_USD", DEFAULT_CEILING_USD))


def default_ledger_path() -> pathlib.Path:
    """Where this installation keeps what it has spent."""
    root = os.environ.get("XDG_CONFIG_HOME") or (pathlib.Path.home() / ".config")
    return pathlib.Path(root) / "voice-bridge" / "spend.json"


class Ledger:
    """What has been spent this month, and whether another session may start."""

    def __init__(self, path: pathlib.Path | None = None, month: str | None = None) -> None:
        """Read the ledger at `path`, counting against `month`."""
        self.path = path or default_ledger_path()
        self.month = month or dt.datetime.now(tz=dt.UTC).strftime("%Y-%m")

    def seconds_spent(self) -> int:
        """Seconds of open microphone this month, and none from any other."""
        try:
            kept = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return 0
        return int(kept.get(self.month, 0))

    def record(self, seconds: float) -> None:
        """Add a session's seconds to the month."""
        try:
            kept = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            kept = {}
        kept[self.month] = int(kept.get(self.month, 0)) + int(seconds)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(kept, indent=1, sort_keys=True))

    def spent_usd(self) -> float:
        """What this month has cost so far."""
        return self.seconds_spent() / 60 * USD_PER_MINUTE

    def remaining_usd(self) -> float:
        """What is left of the ceiling, never below zero."""
        return max(0.0, ceiling_usd() - self.spent_usd())

    def remaining_minutes(self) -> int:
        """What is left, in the unit a person thinks in."""
        return int(self.remaining_usd() / USD_PER_MINUTE)

    def authorise(self) -> None:
        """Raise `Refused` unless another session may start this month."""
        # RULE: a session is refused once the monthly ceiling is spent
        if self.remaining_usd() <= 0:
            message = (
                f"the ceiling for {self.month} is spent: ${self.spent_usd():.2f} of ${ceiling_usd():.2f}"
            )
            raise Refused(message)
