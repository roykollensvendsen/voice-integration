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

#: The language the session speaks. It is a setting rather than a constant
#: because the instructions have to be written in it: the prompting guide says
#: to "write your prompt in the language you want the model to speak", and an
#: English prompt is why the first real conversation came back in German.
LANGUAGE = os.environ.get("VOICE_BRIDGE_LANGUAGE", "nb")

#: Five sentences, the same every session so there is nothing to drift. The
#: reasoning is `docs/voice-contract.md`; the words are policy and live here
#: rather than in the page, which is code a browser was handed.
#:
#: This repository is written in English and these are not: they are a prompt,
#: and the guide is explicit that the prompt has to be in the target language.
#: The first line is the rule the guide prescribes, verbatim in shape.
INSTRUCTIONS: dict[str, str] = {
    "nb": (
        "Snakk norsk med mindre brukeren ber om noe annet. "
        "Du er stemmen til et agentsystem, ikke agenten selv. "
        "Svar selv på småprat, allmennkunnskap og spørsmål om deg selv eller samtalen. "
        "Spør bakenden bare når brukeren vil ha noe gjort på maskinen — kode, filer, "
        "kommandoer, agenter. Bestem aldri selv hva som skal gjøres der. "
        "Les aldri opp en identifikator, en filsti eller et tidsstempel. De står på skjermen. "
        "Si det bakenden gir deg, og stopp."
    ),
    "en": (
        "Speak English unless the user asks to switch. "
        "You are the voice of an agent system, not the agent. "
        "Answer small talk, general knowledge and questions about yourself or this "
        "conversation on your own. Ask the backend only when the person wants "
        "something done on the machine — code, files, commands, agents. Never decide "
        "what happens there yourself. "
        "Never read out an identifier, a file path or a timestamp. They are on the screen. "
        "Say what the backend gives you, then stop."
    ),
}


#: What the model is told to say while the backend works. Written in each
#: language for the same reason the instructions are: a prompt is in the
#: language it produces. Without it a slow answer is silence, and silence on a
#: phone call is indistinguishable from a dropped one.
HOLDING: dict[str, str] = {
    "nb": "Si kort at du setter i gang, og vent.",
    "en": "Say briefly that you are on it, then wait.",
}


#: What counts as answering a permission question. Nothing outside these lists
#: is treated as an answer: a channel that mishears short words must not guess
#: at a yes, and ADR-VI-003 already limits a spoken answer to this one call.
YES: dict[str, tuple[str, ...]] = {
    "nb": ("ja", "ja takk", "greit", "kjør", "kjør det", "gjør det", "ok", "okay"),
    "en": ("yes", "yes please", "go ahead", "do it", "run it", "ok", "okay"),
}
NO: dict[str, tuple[str, ...]] = {
    "nb": ("nei", "nei takk", "stopp", "ikke", "la være", "avbryt"),
    "en": ("no", "no thanks", "stop", "don't", "do not", "cancel"),
}


def answer_to_a_question(said: str, language: str | None = None) -> str | None:
    """`once`, `deny`, or None when that was not an answer at all."""
    spoken = said.strip().strip(".!?,").casefold()
    chosen = language or LANGUAGE
    if spoken in YES.get(chosen, ()) or spoken in YES["en"]:
        return "once"
    if spoken in NO.get(chosen, ()) or spoken in NO["en"]:
        return "deny"
    return None


def holding(language: str | None = None) -> str:
    """What to say while the work runs."""
    return HOLDING.get(language or LANGUAGE, HOLDING["en"])


def instructions(language: str | None = None) -> str:
    """The session instructions, in the language the session speaks."""
    chosen = language or LANGUAGE
    # RULE: a session is never opened without a language rule in its own language
    if chosen not in INSTRUCTIONS:
        message = f"no instructions written in {chosen!r}; the prompt must be in the language it speaks"
        raise Refused(message)
    return INSTRUCTIONS[chosen]


#: How much of the last conversation a new session is given. `input` is a
#: startup field — the guide is explicit that it cannot replace history in a
#: running session — so this is the one chance to resume a topic. It is bounded
#: because a voice session should hold the last few turns and not a diary.
TURNS_REMEMBERED = 12


def session_config(
    language: str | None = None,
    history: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """What the session is created with, and deliberately nothing more."""
    return {
        "input": list(history or [])[-TURNS_REMEMBERED:],
        "model": MODEL,
        # Client delegation: the backend is ours, so the Live session is told
        # about no tools at all. ADR-VI-019 is why.
        "delegation": {"type": "client"},
        "instructions": instructions(language),
    }


def open_session(
    offer_sdp: str,
    ledger: Ledger | None = None,
    key: str | None = None,
    language: str | None = None,
    history: list[dict[str, object]] | None = None,
) -> str:
    """Exchange the page's offer for an answer, or refuse and say why."""
    # RULE: the month is checked before a session is opened
    (ledger or Ledger()).authorise()
    token = key if key is not None else os.environ.get("OPENAI_API_KEY", "")
    if not token:
        message = "no OPENAI_API_KEY, so no voice session can be opened"
        raise Refused(message)
    body = json.dumps(
        {"transport": {"type": "webrtc", "sdp": offer_sdp}, "session": session_config(language, history)}
    )
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
