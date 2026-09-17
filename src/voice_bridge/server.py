"""The bridge: it serves the page, opens the session, and answers a delegation.

Three routes and no framework. A threaded server from the standard library is
enough for one person talking to their own machine, and it keeps the process
holding two keys small enough to read — which was
[ADR-VI-006]'s argument, given up in ADR-VI-018 and mostly kept anyway.

    GET  /                the page
    GET  /config          one phrase, in the session's language
    GET  /watch           every run's lifecycle, as server-sent events
    POST /spent           seconds of open microphone, booked against the month
    POST /session         the browser's WebRTC offer, exchanged for an answer
    POST /delegation      a transcript, answered with something to say aloud

The page never sees a key. It cannot: it is code handed to a browser.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from voice_bridge import gateway, live, quick
from voice_bridge.budget import Ledger
from voice_bridge.policy import Capabilities, Refused
from voice_bridge.speech import say

PAGE = pathlib.Path(__file__).parent / "client" / "index.html"

#: How often a watcher is handed what has arrived.
WATCH_POLL_SECONDS = 0.4

#: What the gateway is told about this particular turn. A voice turn has to end
#: with something to say: dispatching work to a background subagent completes
#: the run immediately, and the real answer arrives later as a message nobody is
#: listening for. Heard from the person's side, that is the system saying "I am
#: starting it" and then never coming back.
TURN_INSTRUCTIONS = (
    "This request came in by voice. A person is listening and will answer by speaking. "
    # Heard aloud, verbatim: "CLOCK: 2026-09-17T12:38:47+02:00 DISK (/home):
    # Totalt 692G, Brukt 651G, Ledig 5,6G, 100% brukt MINNE: ..." — a wall of
    # command output, cut off mid-number by the spoken-length cap. The person's
    # own words: "why did you give me more information than I asked for".
    # Heard aloud: "ID 562691a8-f468-41cb-a58c-b938f929b14a". Nobody can hold
    # that, write it down or say it back, and nobody needs to.
    "Never say an identifier out loud — not a session, a run, a process or a "
    "file path. Nobody can hold one in their head and they are all on the screen. "
    # Asked in passing whether questions were going to one place, it set up a
    # standing rule to forward everything there, started a second coding agent,
    # and began talking to one coding agent through another.
    "Decide who does each request as it arrives, and never set up a standing "
    "rule to send everything somewhere until told otherwise. Answer questions "
    "about this conversation yourself. Send work to a coding agent only when it "
    "needs a repository, a file or a command, and never reach one coding agent "
    "through another. "
    "Answer in one or two spoken sentences and stop. Round numbers and say the "
    "unit. Never pass on raw command output, a table, a heading, a bullet list, "
    "a path, a timestamp or a figure to more than two significant digits. If a "
    "tool gave you a wall of text, read it and say what it means; the detail is "
    "already on the person's screen. Do not explain how you did it, do not offer "
    "next steps, and do not describe how the system works unless that is what "
    "was asked. "
    "Never ask them to reply with exact words, a quoted phrase, or a number from a list. "
    "Do the work in this turn and answer with the result. "
    "Do not dispatch background subagents; run the tools yourself and wait for them. "
    "If it truly cannot be finished now, say in one sentence what you started and what is left. "
    # Everything below is here because the gateway asked, out loud, for one of
    # four numbered options containing file paths and hyphenated flags. Nobody
    # can say that back. A question a person cannot answer is worse than no
    # question: the work simply stops.
    # Five attempts at driving an interactive coding agent through its own
    # screen produced five "no visible answer"; the same question in print mode
    # answered correctly every time. ADR-VI-020.
    "Reach a coding agent in print mode and read its output directly: "
    "`claude -p '<question>' --output-format json`, which answers with the text, "
    "the session identifier, the duration and the cost. Keep that session "
    "identifier and add `--resume <session-id>` to every later question in this "
    "conversation, so the agent remembers what was already said and does not read "
    "the project again from nothing. "
    "Never type into an interactive session on a screen and read the screen back, "
    "unless the person asked for a session they will use themselves. "
    # The person's own words, at the point they gave up: "why are you asking me
    # this, I do not know why I should choose this". Being asked to pick between
    # two ways of doing the same thing is not a question — it is the work,
    # handed back.
    "Do not ask the person to choose how you do something, or whether to try "
    "another way when one fails, or which of two sources to trust. Decide, do it, "
    "and say what you did in one sentence. Ask only about things that are theirs "
    "to decide: permission to change or run something, and what they actually want. "
    "When you need something from the person, ask one short question they can "
    "answer in a few spoken words. Never require exact wording, never read out a "
    "numbered list of options, never ask them to say a file path, a flag, a "
    "setting name or anything with punctuation in it. Offer at most two choices "
    "and name them in ordinary words. If you need a detail they cannot say, pick "
    "the sensible default, say which one you picked, and carry on."
)

#: The startup history is capped at 8,192 tokens across every message. Four
#: characters to the token is the usual rough measure, and this stays well under
#: it: being cut off mid-resume is worse than resuming less.
HISTORY_CHARACTERS = 24_000

#: How long a conversation is worth resuming. Come back an hour later and you
#: are starting something new, whatever the page still shows.
REMEMBER_FOR_SECONDS = 45 * 60

#: How many events the screen keeps. A run is a few dozen; a long session is
#: thousands, and nobody scrolls back that far.
WATCH_KEPT = 400


#: A phrase the last answer demanded back word for word. The gateway keeps
#: asking for these however often it is told not to, and a person walking down
#: the street cannot pronounce «Ja, kjør claude» on cue any more than they can
#: read out a session identifier.
DEMANDED = re.compile(
    r"(?:n\u00f8yaktig|eksakt|exactly|precisely|reply with|svar)"
    r"\s*[:\-]?\s*[\u00ab\"\u201c]"
    r"([^\u00bb\"\u201d\n]{2,60})[\u00bb\"\u201d]",
    re.IGNORECASE,
)


def demanded_phrase(spoken: str) -> str | None:
    """The words an answer insisted on hearing back, if it insisted on any."""
    found = DEMANDED.search(spoken)
    return found.group(1).strip() if found else None


def still_running(payload: object) -> bool:
    """Whether there is more to come, so somebody should keep waiting."""
    return isinstance(payload, dict) and payload.get("status") in ("queued", "running")


#: How a delegation becomes work. The transcript is the only thing the model
#: gives us, so the gateway is asked to plan against it — which is the whole
#: argument of ADR-VI-001, arriving here as one HTTP call.
#:
#: The room is also the gateway's memory, and a room remembers how things were
#: done — including badly. A hundred turns of driving a coding agent through its
#: terminal outweighed both the skill and the instruction telling it not to, and
#: it kept reaching for a session that no longer existed. Changing the room is
#: how you stop paying for a habit.
#:
#: It is named for the orchestrator rather than for the voice, because that is
#: whose conversation it is. The voice holds a few turns and forgets them; this
#: is where the thinking and the memory live.
ROOM = os.environ.get("VOICE_BRIDGE_ROOM", "orchestrator")


def as_said(transcript: str) -> str:
    """What was heard, as the separate things it was, not one run-on line.

    The page sends its turns one to a line. Flattening them into a single
    sentence produced requests like "can we do something meanwhile yes run
    claude", which reads as one confused instruction rather than a question and
    then an answer to a different one.
    """
    # RULE: separate things said stay separate when they are sent on
    said = [line.strip() for line in transcript.splitlines() if line.strip()]
    return "\n".join(said)


def notice(server: Bridge, event: dict[str, Any]) -> None:
    """Keep an event for whoever is watching, and no more than a screenful."""
    # A run can ask for permission long after we stopped waiting for it, so the
    # question is caught here rather than by whoever happened to be polling.
    # RULE: a permission question is noticed however late it arrives
    if str(event.get("event", "")).startswith("approval.request"):
        server.awaiting = str(event.get("run_id") or server.awaiting or "")
    with server.watching_lock:
        server.watching.append(event)
        del server.watching[:-WATCH_KEPT]


def resolve_pending(bridge: Bridge, choice: str) -> str:
    """Answer the permission question the room is waiting on."""
    run_id, bridge.awaiting = bridge.awaiting, None
    if not run_id:
        return "There is nothing waiting for permission."
    spoken = gateway.call(
        "approval_resolve", {"run_id": run_id, "choice": choice}, bridge.gateway_url, bridge.capabilities
    )
    if choice == "deny":
        return spoken
    finished = gateway.wait_for(run_id, bridge.gateway_url)
    if isinstance(finished, dict) and finished.get("status") == "waiting_for_approval":
        bridge.awaiting = run_id
    return say("run_status", finished)


def said_for_them(bridge: Bridge, transcript: str) -> str:
    """Substitute the phrase an answer demanded, when the person simply agreed."""
    if bridge.demanded and live.answer_to_a_question(transcript) == "once":
        # RULE: a phrase the gateway demanded is said for the person, not by them
        transcript, bridge.demanded = bridge.demanded, None
    return transcript


def pending_answer(bridge: Bridge, transcript: str) -> str | None:
    """Resolve a waiting permission question, if this was an answer to one."""
    if not bridge.awaiting:
        return None
    answered = live.answer_to_a_question(transcript)
    # RULE: only a word that is plainly yes or no answers a permission question
    if answered is None:
        return None
    return resolve_pending(bridge, answered)


def answered_here(bridge: Bridge, transcript: str) -> tuple[str | None, str]:
    """Whatever the bridge can settle without the gateway, and what is left to send."""
    # RULE: a question the bridge can answer never travels further
    immediate = quick.answer(bridge, transcript)
    if immediate is not None:
        return immediate, transcript
    transcript = said_for_them(bridge, transcript)
    return pending_answer(bridge, transcript), transcript


def answer_delegation(  # noqa: PLR0913 — a turn needs all six, and bundling them hides what it uses
    transcript: str,
    url: str,
    *,
    capabilities: Capabilities | None = None,
    patience: float = gateway.PATIENCE_SECONDS,
    watcher: Callable[[str, str], None] | None = None,
    bridge: Bridge | None = None,
) -> str:
    """Turn what was heard into something to say back."""
    if not transcript.strip():
        return "I did not catch that."
    # A question that is waiting takes precedence over a new request: "yes" is
    # an answer to it, not a thing to go and do.
    if bridge is not None:
        here, transcript = answered_here(bridge, transcript)
        if here is not None:
            return here
    arguments: dict[str, Any] = {
        "agent": "hermes-agent",
        "instruction": as_said(transcript),
        "room": ROOM,
    }
    (capabilities or Capabilities()).permit("agent_task", arguments)
    planned = gateway.plan("agent_task", arguments, url)
    # RULE: a voice turn asks the gateway to finish inside it
    carrying: dict[str, Any] = {"instructions": TURN_INSTRUCTIONS}
    if bridge is not None:
        # RULE: a request carries the conversation it came out of
        carrying["conversation_history"] = bridge.context()
    asking = replace(planned, body={**(planned.body or {}), **carrying})
    started = gateway.send(asking)
    run_id = started.get("run_id") if isinstance(started, dict) else None
    if not run_id:
        return say("agent_task", started)
    if watcher is not None:
        watcher(str(run_id), as_said(transcript))
    # RULE: a delegation waits for the work rather than reading back a receipt
    finished = gateway.wait_for(str(run_id), url, patience)
    if bridge is not None:
        if isinstance(finished, dict) and finished.get("status") == "waiting_for_approval":
            bridge.awaiting = str(run_id)
        # RULE: a turn is finished only when the run behind it is
        bridge.following = str(run_id) if still_running(finished) else None
    spoken = say("run_status", finished)
    if bridge is not None:
        bridge.demanded = demanded_phrase(str((finished or {}).get("output") or spoken))
    return spoken


def keep_waiting(run_id: str, url: str, patience: float = gateway.PATIENCE_SECONDS) -> tuple[str, bool]:
    """Wait another stretch for a run, and say what to speak and whether to stop."""
    seen = gateway.wait_for(run_id, url, patience)
    return say("run_status", seen), not still_running(seen)


class _Handler(BaseHTTPRequestHandler):
    """The three routes, and nothing else reachable."""

    server: Bridge

    def log_message(self, *_args: object) -> None:
        """Say nothing: the default writes every request to stderr."""

    def _send(self, status: int, payload: dict[str, Any] | None = None, page: bytes = b"") -> None:
        body = page or json.dumps(payload or {}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8" if page else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) or b"{}"
        loaded = json.loads(raw)
        return loaded if isinstance(loaded, dict) else {}

    def do_GET(self) -> None:
        """Serve the page, and only the page."""
        if self.path in ("/", "/index.html"):
            self._send(200, page=PAGE.read_bytes())
        elif self.path == "/watch":
            self._stream()
        elif self.path == "/config":
            # The page needs one phrase in the session's language and nothing
            # else. It is never given a key, a model name or a gateway address.
            self._send(200, {"holding": live.holding()})
        else:
            self._send(404, {"error": "no such path"})

    def _stream(self) -> None:
        """Send what has happened, then everything that happens next."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        sent = 0
        try:
            while True:
                with self.server.watching_lock:
                    pending = self.server.watching[sent:]
                    sent = len(self.server.watching)
                for event in pending:
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                if not pending:
                    self.wfile.write(b": still here\n\n")
                self.wfile.flush()
                time.sleep(WATCH_POLL_SECONDS)
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_POST(self) -> None:
        """Open a session, or answer a delegation."""
        try:
            body = self._read()
            if self.path == "/session":
                sdp = live.open_session(
                    str(body.get("sdp", "")), self.server.ledger, history=self.server.recent()
                )
                self._send(200, {"sdp": sdp, "resumed": len(self.server.recent())})
            elif self.path == "/approval":
                choice = str(body.get("choice", ""))
                if choice not in ("once", "deny"):
                    self._send(400, {"error": "a permission is answered once or deny"})
                else:
                    self._send(200, {"content": resolve_pending(self.server, choice)})
            elif self.path == "/spent":
                # RULE: an open microphone is booked while it is open
                self.server.ledger.record(float(body.get("seconds", 0)))
                self._send(200, {"remaining_usd": round(self.server.ledger.remaining_usd(), 2)})
            elif self.path == "/turn":
                self.server.remember(str(body.get("who", "")), str(body.get("text", "")))
                self._send(200, {})
            elif self.path == "/delegation":
                self.server.following = None
                spoken = answer_delegation(
                    str(body.get("transcript", "")),
                    self.server.gateway_url,
                    capabilities=self.server.capabilities,
                    watcher=self.server.follow,
                    bridge=self.server,
                )
                self._send(
                    200,
                    {
                        "content": spoken,
                        "run_id": self.server.following,
                        "finished": self.server.following is None,
                    },
                )
            elif self.path == "/run":
                spoken, done = keep_waiting(str(body.get("run_id", "")), self.server.gateway_url)
                self._send(200, {"content": spoken, "finished": done})
            else:
                self._send(404, {"error": "no such path"})
        except Refused as refusal:
            self._send(403, {"error": str(refusal)})
        except json.JSONDecodeError:
            self._send(400, {"error": "that was not JSON"})


class Bridge(ThreadingHTTPServer):
    """The server, carrying the few things a request needs."""

    def __init__(self, address: tuple[str, int], gateway_url: str, ledger: Ledger | None = None) -> None:
        """Listen on `address`, talking to the gateway at `gateway_url`."""
        super().__init__(address, _Handler)
        self.gateway_url = gateway_url
        self.ledger = ledger or Ledger()
        self.capabilities = Capabilities()
        self.watching: list[dict[str, Any]] = []
        self.watching_lock = threading.Lock()
        # The transcript belongs here rather than in the page. The delegation
        # guide asks the application to keep it, and a page keeps it only until
        # it is reloaded.
        self.spoken: list[tuple[float, str, str]] = []
        #: The run whose permission question is open, if one is.
        self.awaiting: str | None = None
        #: The run the last request left unfinished, if it left one.
        self.following: str | None = None
        #: A phrase the last answer insisted on hearing back word for word.
        self.demanded: str | None = None

    def remember(self, who: str, text: str) -> None:
        """Keep a turn, for whoever needs to know what was already said."""
        if not text.strip():
            return
        self.spoken.append((time.time(), "user" if who == "You" else "assistant", text.strip()))
        del self.spoken[: -live.TURNS_REMEMBERED * 2]

    def _worth_keeping(self) -> list[tuple[str, str]]:
        """The turns worth passing on: recent enough, few enough, short enough."""
        oldest = time.time() - REMEMBER_FOR_SECONDS
        fresh = [(role, text) for when, role, text in self.spoken if when >= oldest]
        kept: list[tuple[str, str]] = []
        room = HISTORY_CHARACTERS
        for role, text in reversed(fresh[-live.TURNS_REMEMBERED :]):
            if len(text) > room:
                break
            room -= len(text)
            kept.insert(0, (role, text))
        return kept

    def recent(self) -> list[dict[str, Any]]:
        """The turns a new voice session is given, in the shape it takes."""
        # A user message carries `input_text` and an assistant one
        # `output_text`; a plain string is refused outright, which is how this
        # was found. The list takes 128 messages and 8,192 tokens together.
        return [
            {
                "type": "message",
                "role": role,
                # RULE: a remembered turn is a message item, not a bare string
                "content": [{"type": "input_text" if role == "user" else "output_text", "text": text}],
            }
            for role, text in self._worth_keeping()
        ]

    def context(self) -> list[dict[str, str]]:
        """The same turns, in the shape the gateway takes them.

        The gateway plans against what was said, and most of what was said it
        never hears: the voice answers small talk itself. Without this, "run the
        tests there" arrives with no idea what "there" is.
        """
        return [{"role": role, "content": text} for role, text in self._worth_keeping()]

    def follow(self, run_id: str, asked: str) -> None:
        """Relay a run's events to whoever is watching, on its own thread."""
        notice(self, {"event": "run.asked", "run_id": run_id, "asked": asked})

        def read() -> None:
            try:
                for event in gateway.events(run_id, self.gateway_url):
                    notice(self, event)
            except (OSError, Refused) as failure:
                notice(self, {"event": "watch.lost", "run_id": run_id, "why": str(failure)})

        threading.Thread(target=read, daemon=True).start()
