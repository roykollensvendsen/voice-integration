"""What happened in a long session, summed up outside anybody's context. digest_session."""

import pytest
from conftest import TOKEN

from voice_bridge import budget, live, server, sessions


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


def test_a_session_is_summed_up_in_the_voices_own_language(bridge, claude_voice, hermes):
    spoken = say(bridge, "oppsummer build-7c")
    assert spoken == "Økta har rettet to tester og venter nå på en gjennomgang."
    asked = next(a for n, a in claude_voice.called if n == "digest_session")
    assert asked == {"session": "build-7c", "language": live.LANGUAGE_NAMES[live.LANGUAGE]}
    assert hermes.seen == []


def test_what_happened_in_a_session_is_asked_the_same_way(bridge, claude_voice):
    say(bridge, "hva har skjedd i hydropower")
    assert next(a for n, a in claude_voice.called if n == "digest_session")["session"] == "build-7c"


def test_a_summary_too_long_to_hear_ends_on_a_whole_sentence(bridge, claude_voice):
    """A live summary came back longer than promised, ending in an ellipsis."""
    long = "Første setning er her. " * 30 + "Og så noe som ble kuttet…"
    claude_voice.digest = long
    spoken = say(bridge, "oppsummer build-7c")
    assert spoken.endswith(".")
    assert len(spoken) <= server.SPOKEN_ANSWER


def test_a_summary_of_a_name_that_could_be_two_sessions_asks_which(bridge, claude_voice):
    spoken = say(bridge, "oppsummer notes")
    assert "notes-2b" in spoken
    assert "notes-9f" in spoken
    assert "digest_session" not in [n for n, _ in claude_voice.called]


def test_a_summary_is_given_long_enough_to_be_written(bridge, claude_voice, monkeypatch):
    monkeypatch.setattr(sessions, "CALL_SECONDS", 0.5)
    monkeypatch.setattr(server, "DIGEST_SECONDS", 2)
    claude_voice.slow_tools = {"digest_session": 1.0}
    assert "venter" in say(bridge, "oppsummer build-7c")
