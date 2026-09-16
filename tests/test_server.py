"""The three routes the browser can reach, and nothing else."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from voice_bridge import budget, server


@pytest.fixture
def bridge(url, tmp_path):
    """The bridge, talking to the stand-in gateway, on a real port."""
    running = server.Bridge(("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"))
    thread = threading.Thread(target=running.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{running.server_port}"
    finally:
        running.shutdown()
        running.server_close()
        thread.join(timeout=5)


def post(where: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        where, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as failure:
        return failure.status, json.loads(failure.read())


def test_the_page_is_served_at_the_root(bridge):
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert reply.status == 200
    assert "<title>voice-bridge</title>" in page


def test_the_page_carries_no_key(bridge):
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert "sk-" not in page
    assert "Authorization" not in page


def test_nothing_else_is_reachable(bridge):
    with pytest.raises(urllib.error.HTTPError) as refused:
        urllib.request.urlopen(f"{bridge}/../etc/passwd", timeout=10)
    assert refused.value.status == 404


def test_a_delegation_becomes_a_run_and_comes_back_as_a_sentence(bridge, hermes):
    status, body = post(f"{bridge}/delegation", {"transcript": "run the tests"})
    assert status == 200
    assert body["content"] == "The tests pass."
    path, sent, _ = hermes.seen[0]
    assert path == "/v1/runs"
    assert sent == {"input": "run the tests", "model": "hermes-agent", "session_id": "voice"}


def test_an_empty_transcript_is_not_sent_anywhere(bridge, hermes):
    status, body = post(f"{bridge}/delegation", {"transcript": "   "})
    assert status == 200
    assert body["content"] == "I did not catch that."
    assert hermes.seen == []


def test_a_delegation_waits_for_the_work_rather_than_reading_back_a_receipt(bridge, hermes):
    """A run identifier is not an answer, and nobody asks a question to be given one."""
    _, body = post(f"{bridge}/delegation", {"transcript": "run the tests"})
    assert "run_ab12" not in body["content"]
    assert hermes.polls >= 2


def test_work_that_outlasts_our_patience_hands_the_identifier_back(url):
    spoken = server.answer_delegation("run the tests", url, patience=0.0)
    assert spoken == "Still working. Ask me about run_ab12."


def test_a_spent_month_refuses_the_session_rather_than_opening_one(bridge, tmp_path):
    budget.Ledger(tmp_path / "spend.json").record(400 * 60)
    status, body = post(f"{bridge}/session", {"sdp": "v=0"})
    assert status == 403
    assert "ceiling" in body["error"]


def test_the_page_is_given_one_phrase_and_nothing_else(bridge):
    with urllib.request.urlopen(f"{bridge}/config", timeout=10) as reply:
        config = json.loads(reply.read())
    assert set(config) == {"holding"}
    assert config["holding"] == "Si kort at du setter i gang, og vent."
