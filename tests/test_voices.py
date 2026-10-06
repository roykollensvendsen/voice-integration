"""Each target speaks with its own voice, and the person can list and pick them."""

import json
import threading
import urllib.error
import urllib.request

import pytest
from conftest import TOKEN

from voice_bridge import budget, live, server, sessions, target


@pytest.fixture
def bridge(url, tmp_path, claude_voice):
    running = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    running.sessions = sessions.Client(f"http://127.0.0.1:{claude_voice.server_port}/mcp", TOKEN)
    yield running
    running.server_close()


def say(bridge, words):
    return server.answer_delegation(words, bridge.gateway_url, bridge=bridge)


def post(where, payload):
    request = urllib.request.Request(
        where, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as failure:
        return failure.status, json.loads(failure.read())


def test_a_session_is_configured_with_the_voice_it_is_given():
    assert live.session_config(voice="quartz")["audio"] == {"output": {"voice": "quartz"}}


def test_a_session_opens_in_the_voice_of_the_chosen_target(bridge, monkeypatch):
    opened = []
    monkeypatch.setattr(live, "open_session", lambda *_a, voice, **_k: opened.append(voice) or "v=0")

    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        where = f"http://127.0.0.1:{bridge.server_port}/session"
        post(where, {"sdp": "v=0"})
        say(bridge, "snakk med build-7c")
        _, body = post(where, {"sdp": "v=0"})
        say(bridge, "snakk med stemmen")
        post(where, {"sdp": "v=0"})
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
    assert opened == ["cedar", "quartz", "marin"]
    assert body["voice"] == "quartz"


def test_a_chosen_session_hears_everything_that_is_said(bridge, monkeypatch):
    """The voice answered most things itself, and the chosen session saw almost nothing."""
    steered = []
    monkeypatch.setattr(live, "open_session", lambda *_a, steer, **_k: steered.append(steer) or "v=0")
    say(bridge, "snakk med build-7c")
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        post(f"http://127.0.0.1:{bridge.server_port}/session", {"sdp": "v=0"})
        with urllib.request.urlopen(f"http://127.0.0.1:{bridge.server_port}/target", timeout=10) as reply:
            listed = json.loads(reply.read())
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
    assert "build-7c" in steered[0]
    assert "aldri selv" in steered[0]
    assert listed["steer"] == steered[0]


def test_the_voice_alone_answers_by_itself_but_still_passes_on_yes_and_no():
    said = target.steer(target.Target("voice"))
    assert "svar selv" in said
    assert "ja eller nei" in said


def test_a_session_is_configured_with_what_it_is_told_about_the_target():
    told = live.session_config(steer="Du er bare en stemme.")["instructions"]
    assert told.endswith("Du er bare en stemme.")


def test_which_voices_are_there_is_answered_with_the_names(bridge, hermes):
    spoken = say(bridge, "hvilke stemmer har du")
    assert "vesper" in spoken
    assert "cedar" in spoken
    assert hermes.seen == []


def test_a_spoken_voice_change_sets_the_voice_for_the_chosen_target(bridge, hermes):
    say(bridge, "bytt stemme til vesper")
    assert bridge.voices["hermes"] == "vesper"
    assert bridge.voices["voice"] == "marin"
    assert hermes.seen == []


def test_a_voice_the_service_does_not_offer_is_never_sent(bridge):
    spoken = say(bridge, "bytt stemme til robot")
    assert bridge.voices["hermes"] == "cedar"
    assert "robot" in spoken
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        where = f"http://127.0.0.1:{bridge.server_port}/voice"
        status, _ = post(where, {"kind": "session", "voice": "robot"})
        assert status == 403
        status, body = post(where, {"kind": "session", "voice": "willow"})
        assert status == 200
        assert body["voices"]["session"] == "willow"
    finally:
        bridge.shutdown()
        thread.join(timeout=5)


def test_the_voices_survive_a_restart(bridge, url, tmp_path):
    say(bridge, "bytt stemme til gleam")
    again = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    try:
        assert again.voices["hermes"] == "gleam"
    finally:
        again.server_close()


def test_the_target_route_says_which_voice_is_speaking(bridge):
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{bridge.server_port}/target", timeout=10) as reply:
            listed = json.loads(reply.read())
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
    assert listed["voice"] == "cedar"
    assert listed["voices"] == target.VOICE_DEFAULTS
    assert listed["available"] == list(live.VOICES)


def test_the_page_opens_a_new_session_when_the_voice_must_change():
    page = server.PAGE.read_text()
    assert "speaking !== body.voice" in page
    assert 'fetch("/voice"' in page
