#!/usr/bin/env python3
"""Refuse a choice box in the one Claude Code session somebody is talking to by voice.

A session that opens a choice box stops until somebody answers it at the
keyboard. Messages from the voice queue up behind it, and the person talking
hears nothing. So in the session the voice bridge has chosen, the box is
refused, with the reason the model reads: ask the question in the reply
instead, where the voice reads it out. Every other session, and the same
session once the voice has moved on, keeps its boxes. ADR-VI-030.

Installed as a PreToolUse hook on AskUserQuestion in the user's own Claude
Code settings. It uses only the standard library and allows the box whenever
in doubt: a missing or broken state file means nobody is talking by voice.
"""

import json
import os
import pathlib
import sys

REASON = (
    "Roy snakker med denne økta via stemmen, og en valgboks kan han ikke svare på derfra. "
    "Still spørsmålet i svaret ditt i stedet, kort og i én setning, med høyst to valg "
    "sagt med vanlige ord."
)


def chosen_session() -> str:
    """The id of the session the voice bridge is talking to, or nothing."""
    base = os.environ.get("XDG_STATE_HOME") or str(pathlib.Path.home() / ".local" / "state")
    try:
        chosen = json.loads((pathlib.Path(base) / "voice-bridge" / "target.json").read_text())
    except (OSError, ValueError):
        return ""
    if not isinstance(chosen, dict) or chosen.get("kind") != "session":
        return ""
    return str(chosen.get("claude_session_id") or "")


def main() -> int:
    """Refuse the box if this is the session spoken to; otherwise say nothing."""
    try:
        asked = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    spoken_to = chosen_session()
    if spoken_to and asked.get("session_id") == spoken_to:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": REASON,
                    }
                }
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
