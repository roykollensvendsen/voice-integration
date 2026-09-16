"""The bridge: it serves the page, opens the session, and answers a delegation.

Three routes and no framework. A threaded server from the standard library is
enough for one person talking to their own machine, and it keeps the process
holding two keys small enough to read — which was
[ADR-VI-006]'s argument, given up in ADR-VI-018 and mostly kept anyway.

    GET  /                the page
    POST /session         the browser's WebRTC offer, exchanged for an answer
    POST /delegation      a transcript, answered with something to say aloud

The page never sees a key. It cannot: it is code handed to a browser.
"""

from __future__ import annotations

import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from voice_bridge import gateway, live
from voice_bridge.budget import Ledger
from voice_bridge.policy import Capabilities, Refused

PAGE = pathlib.Path(__file__).parent / "client" / "index.html"

#: How a delegation becomes work. The transcript is the only thing the model
#: gives us, so the gateway is asked to plan against it — which is the whole
#: argument of ADR-VI-001, arriving here as one HTTP call.
ROOM = "voice"


def answer_delegation(transcript: str, url: str, capabilities: Capabilities | None = None) -> str:
    """Turn what was heard into something to say back."""
    if not transcript.strip():
        return "I did not catch that."
    return gateway.call(
        "agent_task",
        {"agent": "hermes-agent", "instruction": transcript.strip(), "room": ROOM},
        url,
        capabilities,
    )


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
        else:
            self._send(404, {"error": "no such path"})

    def do_POST(self) -> None:
        """Open a session, or answer a delegation."""
        try:
            body = self._read()
            if self.path == "/session":
                self._send(200, {"sdp": live.open_session(str(body.get("sdp", "")), self.server.ledger)})
            elif self.path == "/delegation":
                spoken = answer_delegation(
                    str(body.get("transcript", "")), self.server.gateway_url, self.server.capabilities
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
