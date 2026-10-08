"""How the bridge is doing, for the page, the voice and an assistant alike. ADR-VI-031."""

import json
import threading
import urllib.request

import pytest
from conftest import TOKEN

from voice_bridge import budget, metrics, server, sessions


@pytest.fixture
def bridge(url, tmp_path, claude_voice):
    running = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    running.sessions = sessions.Client(f"http://127.0.0.1:{claude_voice.server_port}/mcp", TOKEN)
    yield running
    running.server_close()


def test_the_page_reads_one_summary_of_how_everything_is_doing(bridge):
    metrics.started(bridge.store, restarts_now=None)
    bridge.store.record("tool", "whats_new", ms=12.0, ok=False, detail="refused")
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{bridge.server_port}/health", timeout=10) as reply:
            health = json.loads(reply.read())
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
    assert health["bridge"]["now"]["up_since"]
    assert health["bridge"]["now"]["memory"]["available_mb"] > 0
    assert health["bridge"]["errors"][0]["error"] == "refused"
    assert health["claude_voice"]["tools"][0]["name"] == "ask_active_session"


def test_a_claude_voice_that_cannot_be_asked_is_shown_as_such(bridge):
    bridge.sessions = None
    assert bridge.health()["claude_voice"] == {"unreachable": "claude-voice is not configured"}


def test_how_the_bridge_has_been_doing_is_answered_without_a_model_call(bridge, hermes):
    metrics.started(bridge.store, restarts_now=None)
    bridge.store.record("turn", "hermes", ms=8000.0)
    spoken = server.answer_delegation("hvordan har broen hatt det", bridge.gateway_url, bridge=bridge)
    assert hermes.seen == []
    assert "omstart" in spoken
    assert "sekund" in spoken
    assert "T" not in spoken.split("siden", 1)[1].split(".")[0], "a timestamp nobody can say"


def test_the_page_shows_how_the_system_is_doing():
    page = server.PAGE.read_text()
    assert 'id="health"' in page
    assert 'fetch("/health")' in page
