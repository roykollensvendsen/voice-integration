"""Opening a voice session, which is a WebRTC handshake and a budget check.

`gpt-live-1` is reachable over WebRTC and nothing else, so a session is not a
token the page connects with: the page makes an offer, this exchanges it for an
answer, and the audio flows directly between the browser and OpenAI. The key
never reaches the page, which is the only reason this indirection exists.

The session is created in client delegation mode, so the model is given no
functions. What that means for a turn is `docs/voice-contract.md`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from voice_bridge.budget import Ledger
from voice_bridge.policy import Refused

SESSIONS_URL = "https://api.openai.com/v1/live/sessions"
MODEL = "gpt-live-1"
TIMEOUT_SECONDS = 20.0

#: Four sentences, the same every session so there is nothing to drift. The
#: reasoning is `docs/voice-contract.md`; the words are policy and live here
#: rather than in the page, which is code a browser was handed.
INSTRUCTIONS = (
    "You are the voice of an agent system, not the agent. "
    "Whenever the person wants anything done, ask the backend; never decide yourself. "
    "Read run identifiers back slowly, because that is how they address what you started. "
    "Say what the backend gives you, then stop."
)


def session_config() -> dict[str, object]:
    """What the session is created with, and deliberately nothing more."""
    return {
        "model": MODEL,
        # Client delegation: the backend is ours, so the Live session is told
        # about no tools at all. ADR-VI-019 is why.
        "delegation": {"type": "client"},
        "instructions": INSTRUCTIONS,
    }


def open_session(offer_sdp: str, ledger: Ledger | None = None, key: str | None = None) -> str:
    """Exchange the page's offer for an answer, or refuse and say why."""
    # RULE: the month is checked before a session is opened
    (ledger or Ledger()).authorise()
    token = key if key is not None else os.environ.get("OPENAI_API_KEY", "")
    if not token:
        message = "no OPENAI_API_KEY, so no voice session can be opened"
        raise Refused(message)
    body = json.dumps({"transport": {"type": "webrtc", "sdp": offer_sdp}, "session": session_config()})
    request = urllib.request.Request(
        SESSIONS_URL,
        data=body.encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 — as above
            answer = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as failure:
        detail = json.loads(failure.read() or b"{}").get("error", {}).get("message", "no detail")
        message = f"OpenAI refused the session: {detail}"
        raise Refused(message) from failure
    sdp = _answer_sdp(answer)
    if not sdp:
        message = f"no answer in the session OpenAI created: {sorted(answer)}"
        raise Refused(message)
    return sdp


def _answer_sdp(answer: dict[str, object]) -> str:
    """The answer, wherever the reply happens to carry it."""
    transport = answer.get("transport")
    if isinstance(transport, dict) and isinstance(transport.get("sdp"), str):
        return str(transport["sdp"])
    return str(answer["sdp"]) if isinstance(answer.get("sdp"), str) else ""
