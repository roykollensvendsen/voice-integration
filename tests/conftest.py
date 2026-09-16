"""A real HTTP server speaking the part of Hermes' contract this bridge uses.

Not a mock of the client: a server the client reaches over a socket, so the
walking skeleton runs through URL building, JSON encoding, the transport, the
status handling and the spoken rendering. What it is not is Hermes — it answers
the shapes `docs/hermes-contract.md` states, and the day those shapes are wrong
is the day the contract page is wrong too.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

RUN_ID = "run_ab12"
FAILED_RUN_ID = "run_cd34"


class _Gateway(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        """Say nothing: the default writes every request to stderr."""
        return

    def _reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == f"/v1/runs/{RUN_ID}":
            # A real run is running before it is finished, so a poll has to see
            # both. The first look is always "running".
            self.server.polls += 1
            if self.server.polls < 2:
                self._reply(
                    200,
                    {
                        "object": "hermes.run",
                        "run_id": RUN_ID,
                        "status": "running",
                        "last_event": "tool.started",
                    },
                )
            else:
                self._reply(
                    200,
                    {
                        "object": "hermes.run",
                        "run_id": RUN_ID,
                        "status": "completed",
                        "output": "The tests pass.",
                        "last_event": "run.completed",
                    },
                )
        elif self.path == f"/v1/runs/{FAILED_RUN_ID}":
            # A run that failed is a 200 with the failure inside it, not a refusal.
            self._reply(
                200,
                {
                    "object": "hermes.run",
                    "run_id": FAILED_RUN_ID,
                    "status": "failed",
                    "error": "Provider authentication failed: Unknown provider",
                },
            )
        elif self.path == "/api/sessions":
            self._reply(
                200,
                {
                    "object": "list",
                    "data": [
                        {"id": "evening", "title": "Run the tests", "message_count": 4},
                        {"id": "morning", "title": "Look at the parser", "message_count": 2},
                    ],
                    "has_more": False,
                },
            )
        else:
            self._reply(404, {"error": {"message": f"Run not found: {self.path}"}})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        self.server.seen.append((self.path, body, self.headers.get("Authorization")))
        if self.path == "/v1/runs":
            self._reply(202, {"object": "hermes.run", "run_id": RUN_ID, "status": "queued"})
        elif self.path == f"/v1/runs/{RUN_ID}/approval":
            self._reply(200, {"run_id": RUN_ID, "choice": body.get("choice")})
        elif self.path == f"/v1/runs/{RUN_ID}/steer":
            self._reply(200, {"run_id": RUN_ID, "accepted": True})
        elif self.path == f"/v1/runs/{RUN_ID}/stop":
            self._reply(200, {"run_id": RUN_ID, "status": "stopping"})
        else:
            self._reply(404, {"error": {"message": "no such run"}})


@pytest.fixture
def hermes():
    """A gateway on a real port, yielding its base URL and what it was sent."""
    server = HTTPServer(("127.0.0.1", 0), _Gateway)
    server.seen = []
    server.polls = 0
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def run_id():
    """The run the gateway above is still working on."""
    return RUN_ID


@pytest.fixture
def failed_run_id():
    """A run that finished badly, which is not the same as a refused request."""
    return FAILED_RUN_ID


@pytest.fixture
def url(hermes):
    """Where the gateway under test is listening."""
    return f"http://127.0.0.1:{hermes.server_port}"
