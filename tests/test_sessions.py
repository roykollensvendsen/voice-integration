"""News from Claude Code sessions, heard from claude-voice and answered there.

The stand-in below is a real HTTP server speaking the slice of MCP that
`docs/claude-voice-contract.md` states: a session header handed out by
`initialize`, a bearer token, and replies that come back as server-sent events.
"""

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from voice_bridge import budget, server, sessions
from voice_bridge.policy import Refused

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
        if name == "whats_new":
            result = {"cursor": "b9.f0", "events": NEWS}
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
    running.waiting = {"3"}
    thread = threading.Thread(target=running.serve_forever, daemon=True)
    thread.start()
    try:
        yield running
    finally:
        running.shutdown()
        running.server_close()
        thread.join(timeout=5)


@pytest.fixture
def client(claude_voice):
    return sessions.Client(f"http://127.0.0.1:{claude_voice.server_port}/mcp", TOKEN)


@pytest.fixture
def heard(url, tmp_path, client):
    """A bridge that has been told about request 3, and has not answered it."""
    bridge = server.Bridge(("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"))
    bridge.sessions = client
    bridge.hear(NEWS)
    yield bridge
    bridge.server_close()


def post(where, payload):
    request = urllib.request.Request(
        where, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as failure:
        return failure.status, json.loads(failure.read())


def test_a_call_opens_a_session_and_reads_the_answer_out_of_an_event_stream(client, claude_voice):
    got = client.call("whats_new", {"cursor": "b1.f0"})
    assert got["cursor"] == "b9.f0"
    assert claude_voice.opened == 1


def test_a_session_that_expired_is_opened_again(client, claude_voice):
    client.call("whats_new", {"cursor": "b1.f0"})
    claude_voice.expire = True
    assert client.call("whats_new", {"cursor": "b1.f0"})["cursor"] == "b9.f0"
    assert claude_voice.opened == 2


def test_a_refusal_from_claude_voice_is_a_refusal_here(client):
    with pytest.raises(Refused, match="expired"):
        client.call("approve", {"approval_id": "99"})


def test_the_bridge_calls_claude_voice_only_to_hear_news_and_answer_one_request(client, claude_voice):
    with pytest.raises(Refused):
        client.call("message_active_session", {"name": "build", "message": "rm -rf"})
    assert claude_voice.called == []


def test_old_news_is_never_read_out(client):
    cursor, news = sessions.news(client, None)
    assert cursor == "b9.f0"
    assert news == []


def test_news_after_the_first_look_is_passed_on(client):
    _, news = sessions.news(client, "b1.f0")
    assert [item["kind"] for item in news] == ["finished", "needs_approval", "working"]


def test_an_approval_number_is_never_read_aloud(client):
    _, news = sessions.news(client, "b1.f0")
    asking = news[1]["text"]
    assert "3" not in asking
    assert asking.endswith("Yes or no?")
    assert "3" not in sessions.spoken("Approval 3 for build expired and was refused.")


def test_only_some_news_is_said_aloud(heard):
    told = [e for e in heard.watching if e["event"] == "claude.news"]
    assert [e["aloud"] for e in told] == [True, True, False]


def test_a_plain_yes_or_no_answers_the_coding_session_that_asked(heard, claude_voice, hermes):
    spoken = server.answer_delegation("ja", heard.gateway_url, bridge=heard)
    assert ("approve", {"approval_id": "3"}) in claude_voice.called
    assert hermes.seen == []
    assert "once" in spoken.lower()
    assert heard.asked == {}


def test_a_spoken_answer_settles_a_coding_session_only_when_one_request_waits(heard, claude_voice, hermes):
    heard.asked["4"] = "notes wants to use Edit on a.py. Yes or no?"
    spoken = server.answer_delegation("ja", heard.gateway_url, bridge=heard)
    assert claude_voice.called == []
    assert hermes.seen == []
    assert "2" in spoken
    assert set(heard.asked) == {"3", "4"}


def test_a_request_that_expired_is_forgotten(heard):
    heard.hear([{"session": "build", "kind": "approval_expired", "approval_id": "3", "text": "gone"}])
    assert heard.asked == {}


def test_a_no_refuses_the_coding_session_that_asked(heard, claude_voice):
    server.answer_delegation("nei", heard.gateway_url, bridge=heard)
    assert claude_voice.called[-1] == ("deny", {"approval_id": "3"})


def test_a_request_that_expired_is_said_to_have_gone(heard, claude_voice):
    claude_voice.waiting.clear()
    assert "no longer waiting" in server.answer_delegation("ja", heard.gateway_url, bridge=heard)


def test_a_button_answers_only_a_request_the_bridge_was_told_about(heard, claude_voice):
    thread = threading.Thread(target=heard.serve_forever, daemon=True)
    thread.start()
    try:
        where = f"http://127.0.0.1:{heard.server_port}/approval"
        status, _ = post(where, {"choice": "once", "approval_id": "7"})
        assert status == 403
        assert claude_voice.called == []
        status, _ = post(where, {"choice": "once", "approval_id": "3"})
        assert status == 200
        assert claude_voice.called == [("approve", {"approval_id": "3"})]
    finally:
        heard.shutdown()
        thread.join(timeout=5)


def test_the_token_comes_from_claude_voices_own_file(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_VOICE_TOKEN", raising=False)
    env = tmp_path / "env"
    env.write_text("CLAUDE_VOICE_ROOT=/x\nCLAUDE_VOICE_TOKEN=from-file\n")
    assert sessions.token(env) == "from-file"
    assert sessions.token(tmp_path / "missing") is None


def test_the_page_says_news_only_once_and_only_to_an_open_microphone():
    page = server.PAGE.read_text()
    assert 'e.event === "claude.news"' in page
    assert "e.seq > newsSeen" in page
    assert "fresh && pc && e.aloud" in page
