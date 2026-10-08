"""A spoken "avbryt" stops the work under way, not only the voice. The voice plan's fourth point.

Interrupting the voice silenced it and left the work running: a Hermes run kept
going, and a busy session's answer was spoken minutes later as if still wanted.
"""

import pytest
from conftest import TOKEN

from voice_bridge import budget, server, sessions, target


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


@pytest.mark.parametrize("said", ["avbryt", "avbryt det", "stopp arbeidet", "cancel that", "stop the work"])
def test_a_request_to_cancel_is_recognised(said):
    assert target.cancel_request(said)


@pytest.mark.parametrize(
    "said", ["stopp", "ikke avbryt meg når jeg snakker om testene i morgen tidlig", "kan du stoppe"]
)
def test_quieting_the_voice_or_a_longer_sentence_is_not_a_cancel(said):
    assert not target.cancel_request(said)


def test_cancelling_stops_the_run_the_gateway_is_working_on(bridge, hermes, run_id):
    bridge.open_runs.add(run_id)
    spoken = say(bridge, "avbryt")
    assert (f"/v1/runs/{run_id}/stop") in [path for path, _, _ in hermes.seen]
    assert bridge.open_runs == set()
    assert "Hermes" in spoken


def test_cancelling_drops_an_answer_still_owed_by_a_busy_session(bridge):
    bridge.answers_awaited["build-7c"] = None
    spoken = say(bridge, "avbryt")
    assert "build-7c" in bridge.dropped
    assert "screen" in spoken, "a session that cannot be stopped from here is said to be so"
    bridge.hear([{"session": "build-7c", "kind": "answer", "text": "Old answer."}])
    told = [e for e in bridge.watching if e["event"] == "claude.news"]
    assert not told[-1]["aloud"]


def test_cancelling_stops_the_turn_of_a_session_claude_voice_runs(bridge, claude_voice):
    claude_voice.cancelled = {"cancelled": True, "status": "interrupted", "how": "sdk"}
    bridge.answers_awaited["runner"] = None
    spoken = say(bridge, "avbryt")
    assert ("cancel", {"session_id": "runner"}) in claude_voice.called
    assert "Stopped runner" in spoken


def test_a_terminal_session_is_said_to_be_stoppable_only_at_its_screen(bridge, claude_voice):
    say(bridge, "snakk med build-7c")
    spoken = say(bridge, "avbryt")
    assert ("cancel", {"session_id": "build-7c"}) in claude_voice.called
    assert "screen" in spoken


def test_cancelling_with_nothing_under_way_says_so(bridge, hermes):
    assert "nothing" in say(bridge, "avbryt").lower()
    assert hermes.seen == []
