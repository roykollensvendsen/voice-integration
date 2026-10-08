"""A real HTTP server speaking the part of Hermes' contract this bridge uses.

Not a mock of the client: a server the client reaches over a socket, so the
walking skeleton runs through URL building, JSON encoding, the transport, the
status handling and the spoken rendering. What it is not is Hermes — it answers
the shapes `docs/hermes-contract.md` states, and the day those shapes are wrong
is the day the contract page is wrong too.
"""

import json
import threading
import time
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


TOKEN = "local-secret"  # noqa: S105 — a test value, not a credential

NEWS = [
    {"session": "build", "kind": "finished", "text": "build finished. Done: fixed.", "ts": 1.0},
    {
        "session": "build",
        "kind": "needs_approval",
        "text": "build wants to run Bash: make. Approval 3: yes or no?",
        "approval_id": "3",
        "tool": "Bash",
        "input": {"command": "make"},
        "ts": 2.0,
    },
    {"session": "notes", "kind": "working", "text": "notes is working.", "ts": 3.0},
]


#: What `list_active_sessions` answers, in the shape the real one does.
ACTIVE = [
    {"name": "build-7c", "project": "akso/hydropower", "status": "idle", "claude_session_id": "a1"},
    {"name": "notes-2b", "project": "notes", "status": "busy", "kind": "bg"},
    {"name": "notes-9f", "project": "notes", "status": "idle", "kind": "interactive"},
    {"name": "runner-1a", "project": "cv", "status": "idle", "kind": "bg", "managed_by_bridge": True},
]


#: What `fleet_recap` answers: one line per session about what it is doing.
FLEET = [
    {"id": "a1", "name": "build-7c", "status": "waiting", "doing": "venter på valg: Skal jeg slå sammen?"},
    {"id": "b2", "name": "notes-2b", "status": "busy", "doing": "Skriver om innledningen."},
    {"id": "c3", "name": "notes-9f", "status": "idle", "doing": ""},
]

#: What `session_tree` answers: a subagent under one session, and one message.
TREE = [
    {"id": "claude-voice", "name": "claude-voice", "kind": "bridge", "parent_id": None, "talks_to": []},
    {"id": "a1", "name": "build-7c", "kind": "terminal", "project": "akso/hydropower", "talks_to": ["c3"]},
    {"id": "a1/explore", "name": "explore", "kind": "subagent", "parent_id": "a1", "talks_to": []},
    {"id": "c3", "name": "notes-9f", "kind": "terminal", "project": "notes", "talks_to": []},
]


class _ClaudeVoice(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        """Say nothing: the default writes every request to stderr."""
        return

    def _reply(self, status, payload=None, headers=()):
        body = b"" if payload is None else f"event: message\ndata: {json.dumps(payload)}\n\n".encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        message = json.loads(self.rfile.read(length) or b"{}")
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._reply(401)
            return
        method = message.get("method")
        if method == "initialize":
            self.server.opened += 1
            self._reply(
                200,
                {"jsonrpc": "2.0", "id": message["id"], "result": {"protocolVersion": "2025-06-18"}},
                [("Mcp-Session-Id", f"s{self.server.opened}")],
            )
            return
        if self.headers.get("Mcp-Session-Id") != f"s{self.server.opened}" or self.server.expire:
            self.server.expire = False
            self._reply(404)
            return
        if method == "notifications/initialized":
            self._reply(202)
            return
        name = message["params"]["name"]
        arguments = message["params"].get("arguments") or {}
        self.server.called.append((name, arguments))
        self.server.metas.append(message["params"].get("_meta") or {})
        canned = {
            "whats_new": {"cursor": "b9.f0", "events": NEWS},
            "list_active_sessions": {"sessions": self.server.active},
            "ask_active_session": self.server.answer,
            "read_session_output": self.server.output,
            "session_tree": {"version": "v1", "nodes": TREE},
            "fleet_recap": {"sessions": FLEET},
            "cancel": {"session_id": arguments.get("session_id"), **self.server.cancelled},
            "digest_session": {
                "session": arguments.get("session"),
                "digest": self.server.digest,
                "turns_considered": 40,
                "cut": False,
            },
            "health": {
                "now": {"up_since": "2026-10-08T09:00:00+00:00", "version": "abc1234", "memory_rss_mb": 80},
                "tools": [
                    {"name": "ask_active_session", "calls": 4, "errors": 1, "p50_ms": 4200, "p95_ms": 9000}
                ],
                "errors": [
                    {"at": "2026-10-08T10:00:00+00:00", "tool": "ask_active_session", "error": "boom"}
                ],
            },
        }
        if name == "ask_active_session":
            time.sleep(self.server.slow)
        time.sleep(self.server.slow_tools.get(name, 0.0))
        if name in canned:
            result = canned[name]
        elif arguments.get("approval_id") in self.server.waiting:
            self.server.waiting.discard(arguments["approval_id"])
            result = {"id": arguments["approval_id"]}
        else:
            text = "No such pending approval; it may have expired"
            self._reply(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {"isError": True, "content": [{"type": "text", "text": text}]},
                },
            )
            return
        self._reply(200, {"jsonrpc": "2.0", "id": message["id"], "result": {"structuredContent": result}})


@pytest.fixture
def claude_voice():
    """claude-voice on a real port, recording every tool it is asked to run."""
    running = HTTPServer(("127.0.0.1", 0), _ClaudeVoice)
    running.opened = 0
    running.expire = False
    running.called = []
    running.metas = []
    running.waiting = {"3"}
    running.active = [dict(session) for session in ACTIVE]
    running.answer = {"status": "answered", "reply": "The tests pass.", "next_after": 4}
    running.slow = 0.0
    running.slow_tools = {}
    running.cancelled = {"cancelled": False, "status": "not_supported"}
    running.digest = "Økta har rettet to tester og venter nå på en gjennomgang."
    running.output = {
        "turns": [{"index": 5, "role": "assistant", "text": "Done now."}],
        "next_after": 5,
        "status": "idle",
    }
    thread = threading.Thread(target=running.serve_forever, daemon=True)
    thread.start()
    try:
        yield running
    finally:
        running.shutdown()
        running.server_close()
        thread.join(timeout=5)
