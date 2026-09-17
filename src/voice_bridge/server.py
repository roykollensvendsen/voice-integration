"""The bridge: it serves the page, opens the session, and answers a delegation.

Three routes and no framework. A threaded server from the standard library is
enough for one person talking to their own machine, and it keeps the process
holding two keys small enough to read — which was
[ADR-VI-006]'s argument, given up in ADR-VI-018 and mostly kept anyway.

    GET  /                the page
    GET  /config          one phrase, in the session's language
    GET  /watch           every run's lifecycle, as server-sent events
    POST /session         the browser's WebRTC offer, exchanged for an answer
    POST /delegation      a transcript, answered with something to say aloud

The page never sees a key. It cannot: it is code handed to a browser.
"""

from __future__ import annotations

import json
import pathlib
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from voice_bridge import gateway, live
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


def still_running(payload: object) -> bool:
    """Whether there is more to come, so somebody should keep waiting."""
    return isinstance(payload, dict) and payload.get("status") in ("queued", "running")


#: How a delegation becomes work. The transcript is the only thing the model
#: gives us, so the gateway is asked to plan against it — which is the whole
#: argument of ADR-VI-001, arriving here as one HTTP call.
ROOM = "voice"


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
    if bridge is not None and bridge.awaiting:
        answered = live.answer_to_a_question(transcript)
        # RULE: only a word that is plainly yes or no answers a permission question
        if answered is not None:
            return resolve_pending(bridge, answered)
    arguments: dict[str, Any] = {
        "agent": "hermes-agent",
        "instruction": as_said(transcript),
        "room": ROOM,
    }
    (capabilities or Capabilities()).permit("agent_task", arguments)
    planned = gateway.plan("agent_task", arguments, url)
    # RULE: a voice turn asks the gateway to finish inside it
    asking = replace(planned, body={**(planned.body or {}), "instructions": TURN_INSTRUCTIONS})
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
    return say("run_status", finished)


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
        self.spoken: list[tuple[float, dict[str, Any]]] = []
        #: The run whose permission question is open, if one is.
        self.awaiting: str | None = None
        #: The run the last request left unfinished, if it left one.
        self.following: str | None = None

    def remember(self, who: str, text: str) -> None:
        """Keep a turn, so the next session can be given it."""
        if not text.strip():
            return
        said = who == "You"
        # RULE: a remembered turn is a message item, not a bare string
        turn = {
            "type": "message",
            "role": "user" if said else "assistant",
            # A user message carries `input_text` and an assistant one
            # `output_text`; a plain string is refused outright, which is how
            # this was found.
            "content": [{"type": "input_text" if said else "output_text", "text": text.strip()}],
        }
        self.spoken.append((time.time(), turn))
        del self.spoken[: -live.TURNS_REMEMBERED * 2]

    def recent(self) -> list[dict[str, Any]]:
        """The turns worth resuming: recent enough, few enough, short enough."""
        oldest = time.time() - REMEMBER_FOR_SECONDS
        fresh = [turn for when, turn in self.spoken if when >= oldest]
        # The list takes at most 128 messages and 8,192 tokens together. Turns
        # are counted from the end, because the last thing said matters most.
        kept: list[dict[str, Any]] = []
        room = HISTORY_CHARACTERS
        for turn in reversed(fresh[-live.TURNS_REMEMBERED :]):
            spent = len(str(turn["content"][0]["text"]))
            if spent > room:
                break
            room -= spent
            kept.insert(0, turn)
        return kept

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
