"""What every session is doing, in one call. claude-voice's fleet_recap."""

import json
import threading
import urllib.request

import pytest
from conftest import TOKEN

from voice_bridge import budget, server, sessions


@pytest.fixture
def bridge(url, tmp_path, claude_voice):
    running = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    running.sessions = sessions.Client(f"http://127.0.0.1:{claude_voice.server_port}/mcp", TOKEN)
    yield running
    running.server_close()


def test_what_the_sessions_are_doing_is_answered_in_one_call_without_a_model(bridge, claude_voice, hermes):
    spoken = server.answer_delegation("hva holder øktene på med", bridge.gateway_url, bridge=bridge)
    assert hermes.seen == []
    assert [name for name, _ in claude_voice.called] == ["fleet_recap"]
    assert spoken.index("build-7c") < spoken.index("notes-2b"), "a session waiting on a choice is said first"
    assert "Skal jeg slå sammen?" in spoken
    assert "notes-9f" not in spoken, "a session with nothing to say is left out"
    assert ".." not in spoken, "each line's own full stop is kept, not doubled"
    assert "?." not in spoken


def test_the_tree_shows_what_each_session_is_doing(bridge):
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{bridge.server_port}/target", timeout=10) as reply:
            listed = json.loads(reply.read())
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
    doing = {s["name"]: s.get("doing") for s in listed["sessions"]}
    assert doing["notes-2b"] == "Skriver om innledningen."


def test_the_page_draws_what_a_session_is_doing_under_it():
    assert "s.doing" in server.PAGE.read_text()
