"""Who a turn goes to: the voice alone, the gateway, or one Claude Code session."""

import json
import threading
import urllib.error
import urllib.request

import pytest
from conftest import NEWS, TOKEN

from voice_bridge import budget, server, sessions, target


@pytest.fixture
def bridge(url, tmp_path, claude_voice):
    """A bridge that can reach the stand-in gateway and the stand-in claude-voice."""
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


def test_the_gateway_is_the_target_until_somebody_chooses_otherwise(bridge):
    assert bridge.chosen == target.Target("hermes")


def test_while_the_voice_alone_is_chosen_nothing_is_forwarded(bridge, hermes, claude_voice):
    say(bridge, "snakk med stemmen")
    spoken = say(bridge, "run the tests")
    assert hermes.seen == []
    assert [name for name, _ in claude_voice.called] == []
    assert "nothing" in spoken.lower()


def test_a_name_is_switched_to_only_when_it_matches_exactly_one_session(bridge):
    spoken = say(bridge, "snakk med notes")
    assert bridge.chosen == target.Target("hermes")
    assert "notes-2b" in spoken
    assert "notes-9f" in spoken
    say(bridge, "talk to hydropower")
    assert bridge.chosen == target.Target("session", "build-7c")


def test_an_unknown_name_leaves_the_target_where_it_was(bridge):
    spoken = say(bridge, "snakk med kalenderen")
    assert bridge.chosen == target.Target("hermes")
    assert "kalenderen" in spoken


def test_a_turn_goes_to_the_chosen_session_and_its_reply_is_spoken(bridge, hermes, claude_voice):
    say(bridge, "snakk med build-7c")
    spoken = say(bridge, "kjør testene")
    assert spoken == "The tests pass."
    asked = [arguments for name, arguments in claude_voice.called if name == "ask_active_session"]
    assert asked[0]["session"] == "build-7c"
    assert asked[0]["message"] == "kjør testene"
    assert hermes.seen == []


def test_a_session_is_given_as_long_as_it_was_promised_to_answer(bridge, claude_voice, monkeypatch):
    """A turn waits up to ASK_SECONDS for the session, and the call gave up after ten."""
    monkeypatch.setattr(sessions, "CALL_SECONDS", 0.5)
    monkeypatch.setattr(server, "ASK_SECONDS", 2)
    claude_voice.slow = 1.0
    say(bridge, "snakk med build-7c")
    assert say(bridge, "kjør testene") == "The tests pass."


def test_news_and_permission_answers_come_first_whatever_is_chosen(bridge, claude_voice):
    say(bridge, "snakk med build-7c")
    bridge.hear(NEWS)
    say(bridge, "ja")
    assert ("approve", {"approval_id": "3"}) in claude_voice.called
    assert "ask_active_session" not in [name for name, _ in claude_voice.called]


def test_a_session_that_ended_hands_the_conversation_back_to_the_voice(bridge, claude_voice):
    say(bridge, "snakk med build-7c")
    claude_voice.answer = {"status": "session_ended", "session_ended": True, "reply": ""}
    spoken = say(bridge, "er du der")
    assert bridge.chosen == target.Target("voice")
    assert "build-7c" in spoken


def test_when_the_chosen_session_ends_the_voice_takes_over_and_says_so(bridge):
    say(bridge, "snakk med build-7c")
    bridge.hear([{"session": "build-7c", "kind": "ended", "text": "build-7c has ended."}])
    assert bridge.chosen == target.Target("voice")
    told = [e for e in bridge.watching if e["event"] == "claude.news"][-1]
    assert told["aloud"]
    assert "voice again" in told["said"]


def test_a_session_waiting_at_its_own_screen_stays_chosen(bridge, claude_voice):
    say(bridge, "snakk med build-7c")
    claude_voice.answer = {"status": "needs_input", "session_ended": False, "reply": ""}
    spoken = say(bridge, "fortsett")
    assert bridge.chosen == target.Target("session", "build-7c")
    assert "screen" in spoken


def test_a_long_answer_is_followed_until_the_session_is_idle(bridge, claude_voice):
    say(bridge, "snakk med build-7c")
    claude_voice.answer = {"status": "still_working", "reply": "Starting.", "next_after": 4}
    say(bridge, "kjør alt")
    assert bridge.following is not None
    spoken, done = server.keep_waiting(bridge.following, bridge.gateway_url, bridge=bridge, patience=1)
    assert done
    assert spoken == "Done now."
    assert ("read_session_output", {"session": "build-7c", "after": 4}) in claude_voice.called


def test_talk_to_hermes_sends_turns_to_the_gateway_again(bridge, hermes):
    say(bridge, "snakk med stemmen")
    say(bridge, "prat med hermes")
    say(bridge, "run the tests")
    assert hermes.seen[0][0] == "/v1/runs"


def test_the_choice_survives_a_restart(bridge, url, tmp_path):
    say(bridge, "snakk med build-7c")
    again = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    try:
        assert again.chosen == target.Target("session", "build-7c")
    finally:
        again.server_close()


def test_a_session_is_chosen_from_the_page_only_if_it_is_running(bridge):
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        where = f"http://127.0.0.1:{bridge.server_port}/target"
        status, _ = post(where, {"kind": "session", "name": "not-running"})
        assert status == 403
        status, body = post(where, {"kind": "session", "name": "notes-9f"})
        assert status == 200
        assert body["chosen"] == {"kind": "session", "name": "notes-9f"}
        with urllib.request.urlopen(where, timeout=10) as reply:
            listed = json.loads(reply.read())
        assert [s["name"] for s in listed["sessions"]] == ["build-7c", "notes-2b", "notes-9f"]
        assert listed["chosen"]["name"] == "notes-9f"
        assert {node["id"]: node.get("parent_id") for node in listed["tree"]}["a1/explore"] == "a1"
    finally:
        bridge.shutdown()
        thread.join(timeout=5)


def test_the_tree_is_fetched_again_only_when_it_changed(bridge, claude_voice):
    bridge.tree()
    bridge.tree()
    assert [name for name, _ in claude_voice.called].count("session_tree") == 1
    bridge.hear([{"session": "claude-voice", "kind": "tree_changed", "text": "v2"}])
    bridge.tree()
    assert [name for name, _ in claude_voice.called].count("session_tree") == 2


def test_a_long_sentence_that_mentions_talking_to_someone_is_not_a_switch():
    said = "talk to me about what the build session said this morning when the tests broke"
    assert target.switch_request(said) is None


def test_the_page_shows_who_you_are_talking_to_and_lets_you_tap_another():
    page = server.PAGE.read_text()
    assert 'id="who"' in page
    assert 'fetch("/target"' in page
    assert "Bare stemmen" in page
    assert "talks_to" in page
    assert 'e.kind === "tree_changed"' in page
