#!/usr/bin/env python3
"""Refuse a choice box in the one Claude Code session somebody is talking to by voice.

A session that opens a choice box stops until somebody answers it at the
keyboard. Messages from the voice queue up behind it, and the person talking
hears nothing. So in the session the voice bridge has chosen, the box is
refused, with the reason the model reads: ask the question in the reply
instead, where the voice reads it out. Every other session, and the same
session once the voice has moved on, keeps its boxes. ADR-VI-030.

A session the voice has just sent a message to is spoken to as well, even when
it is not the chosen one. For ten minutes after such a message its boxes are
refused the same way. A message counts as the voice's when it ends with the
line claude-voice adds to every message it carries. It also counts when its
sender runs in a claude-voice courier's folder.

Installed as a PreToolUse hook on AskUserQuestion in the user's own Claude
Code settings. It uses only the standard library and allows the box whenever
in doubt: a missing or broken state file means nobody is talking by voice.
"""

import datetime
import json
import os
import pathlib
import sys

REASON = (
    "Roy snakker med denne økta via stemmen, og en valgboks kan han ikke svare på derfra. "
    "Still spørsmålet i svaret ditt i stedet, kort og i én setning, med høyst to valg "
    "sagt med vanlige ord."
)
JUST_MESSAGED = (
    "Denne økta fikk nettopp en melding via stemmen, og en valgboks kan ikke besvares derfra. "
    "Still spørsmålet i svaret ditt i stedet, kort og i én setning, med høyst to valg "
    "sagt med vanlige ord."
)

#: How long after a voice message the session counts as spoken to.
RECENT = datetime.timedelta(minutes=10)
#: The line claude-voice puts under every message its courier carries.
VOICE_MARK = "Your reply is read by the voice."
#: The folder a claude-voice courier runs in starts with this.
COURIER_FOLDER = "claude-voice-msg-"
#: Only the end of a long transcript is read; ten minutes of it fits in far less.
TAIL_BYTES = 2_000_000


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


def from_courier(origin: dict) -> bool:
    """Whether a message from another session was carried by claude-voice's courier."""
    if str(origin.get("body") or "").rstrip().endswith(VOICE_MARK):
        return True
    config = os.environ.get("CLAUDE_CONFIG_DIR") or str(pathlib.Path.home() / ".claude")
    try:
        record = pathlib.Path(config) / "sessions" / f"{int(origin['verifiedPeerPid'])}.json"
        sender = json.loads(record.read_text())
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return isinstance(sender, dict) and pathlib.Path(str(sender.get("cwd") or "")).name.startswith(
        COURIER_FOLDER
    )


def voice_message_lately(transcript: object, now: datetime.datetime) -> bool:
    """Whether a voice message reached this session in the last ten minutes."""
    try:
        with pathlib.Path(str(transcript)).open("rb") as f:
            f.seek(max(f.seek(0, os.SEEK_END) - TAIL_BYTES, 0))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except (OSError, ValueError):
        return False
    for line in reversed(lines):
        try:
            entry = json.loads(line)
            when = datetime.datetime.fromisoformat(str(entry["timestamp"]))
        except (ValueError, KeyError, TypeError):
            continue
        if now - when > RECENT:
            return False  # everything before it is older still
        origin = entry.get("origin")
        if isinstance(origin, dict) and origin.get("kind") == "peer" and from_courier(origin):
            return True
    return False


def main() -> int:
    """Refuse the box if this session is spoken to; otherwise say nothing."""
    try:
        asked = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if not isinstance(asked, dict):
        return 0
    spoken_to = chosen_session()
    reason = ""
    if spoken_to and asked.get("session_id") == spoken_to:
        reason = REASON
    # RULE: a choice box is refused for ten minutes after a voice message
    elif asked.get("transcript_path") and voice_message_lately(
        asked["transcript_path"], datetime.datetime.now(datetime.UTC)
    ):
        reason = JUST_MESSAGED
    if reason:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
