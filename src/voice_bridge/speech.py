"""Turn a gateway reply into something worth saying out loud.

Audio is the expensive direction and the lossy one. A spoken reply is one or
two sentences and a number; the detail is on the screen, addressed by the
identifier the reply gives back. Nothing here ever reads an agent's output
aloud in full.
"""

from __future__ import annotations

from typing import Any

#: Long enough for two sentences and an identifier, short enough that no
#: transcript can hide inside one. Measured in characters because that is what
#: the text-to-speech side bills and what a listener actually endures.
SPOKEN_REPLY_MAX_CHARS = 320


def shorten(text: str) -> str:
    """Cut a reply to something a person will sit through."""
    collapsed = " ".join(text.split())
    # RULE: a spoken reply is capped, so audio never carries a transcript
    if len(collapsed) <= SPOKEN_REPLY_MAX_CHARS:
        return collapsed
    cut = collapsed[: SPOKEN_REPLY_MAX_CHARS - 1]
    stop = max(cut.rfind(". "), cut.rfind(", "), cut.rfind(" "))
    return (cut[:stop] if stop > 0 else cut).rstrip(" ,.") + "…"


def say(tool_name: str, payload: Any) -> str:  # noqa: ANN401 — a gateway reply is whatever JSON it sent
    """Render one gateway reply as a sentence to speak."""
    if not isinstance(payload, dict):
        return shorten(str(payload))
    # A refusal is an envelope with nothing else in it. A run that failed is a
    # whole object that happens to carry its failure, and `object` is how the
    # gateway distinguishes the two.
    # RULE: a run that failed is not a refused request
    if "error" in payload and "object" not in payload:
        # RULE: a gateway refusal is spoken, not raised
        error = payload["error"]
        detail = error.get("message", "") if isinstance(error, dict) else str(error)
        return shorten(f"The gateway refused that: {detail}")
    renderers = {
        "agent_task": _started,
        "approval_resolve": _approved,
        "run_status": _status,
        "run_steer": _steered,
        "run_stop": _stopped,
        "session_recall": _sessions,
    }
    render = renderers.get(tool_name)
    return shorten(render(payload) if render else str(payload))


def _started(payload: dict[str, Any]) -> str:
    return f"Started. The run is {payload.get('run_id', 'unnamed')}."


def _approved(payload: dict[str, Any]) -> str:
    return f"Answered {payload.get('choice', 'that')}, for this one call."


def _status(payload: dict[str, Any]) -> str:
    state = payload.get("status", "unknown")
    failure = payload.get("error")
    if failure:
        detail = failure.get("message", "") if isinstance(failure, dict) else str(failure)
        return f"That run {state}: {detail}"
    last = payload.get("last_event")
    tail = f", last event {last}" if last else ""
    return f"That run is {state}{tail}."


def _steered(payload: dict[str, Any]) -> str:
    return "Passed it on." if payload.get("accepted", True) else "It would not take that now."


def _stopped(payload: dict[str, Any]) -> str:
    return f"Stopping. The run is {payload.get('status', 'winding down')}."


def _sessions(payload: dict[str, Any]) -> str:
    sessions = payload.get("data") or payload.get("sessions") or []
    if not sessions:
        return "No sessions open."
    # A session is keyed `id`. `session_id` is what it is called everywhere the
    # run API takes one, and reading that here is what made every room "?".
    names = [
        str(s.get("id") or s.get("session_id") or "?") if isinstance(s, dict) else str(s) for s in sessions
    ]
    return f"{len(names)} open: {', '.join(names)}."
