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

#: How many events the screen keeps. A run is a few dozen; a long session is
#: thousands, and nobody scrolls back that far.
WATCH_KEPT = 400

#: How a delegation becomes work. The transcript is the only thing the model
#: gives us, so the gateway is asked to plan against it — which is the whole
#: argument of ADR-VI-001, arriving here as one HTTP call.
ROOM = "voice"


def _note(server: Bridge, event: dict[str, Any]) -> None:
    """Keep an event for whoever is watching, and no more than a screenful."""
    with server.watching_lock:
        server.watching.append(event)
        del server.watching[:-WATCH_KEPT]


def answer_delegation(
    transcript: str,
    url: str,
    capabilities: Capabilities | None = None,
    patience: float = gateway.PATIENCE_SECONDS,
    watcher: Callable[[str, str], None] | None = None,
) -> str:
    """Turn what was heard into something to say back."""
    if not transcript.strip():
        return "I did not catch that."
    arguments: dict[str, Any] = {"agent": "hermes-agent", "instruction": transcript.strip(), "room": ROOM}
    (capabilities or Capabilities()).permit("agent_task", arguments)
    started = gateway.send(gateway.plan("agent_task", arguments, url))
    run_id = started.get("run_id") if isinstance(started, dict) else None
    if not run_id:
        return say("agent_task", started)
    if watcher is not None:
        watcher(str(run_id), transcript.strip())
    # RULE: a delegation waits for the work rather than reading back a receipt
    finished = gateway.wait_for(str(run_id), url, patience)
    return say("run_status", finished)


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
                self._send(200, {"sdp": live.open_session(str(body.get("sdp", "")), self.server.ledger)})
            elif self.path == "/delegation":
                spoken = answer_delegation(
                    str(body.get("transcript", "")),
                    self.server.gateway_url,
                    self.server.capabilities,
                    watcher=self.server.follow,
                )
                self._send(200, {"content": spoken})
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

    def follow(self, run_id: str, asked: str) -> None:
        """Relay a run's events to whoever is watching, on its own thread."""
        _note(self, {"event": "run.asked", "run_id": run_id, "asked": asked})

        def read() -> None:
            try:
                for event in gateway.events(run_id, self.gateway_url):
                    _note(self, event)
            except (OSError, Refused) as failure:
                _note(self, {"event": "watch.lost", "run_id": run_id, "why": str(failure)})

        threading.Thread(target=read, daemon=True).start()
