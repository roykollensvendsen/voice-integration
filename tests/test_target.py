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
    assert "«kjør testene»" in asked[0]["message"]
    assert hermes.seen == []


def test_a_session_is_given_as_long_as_it_was_promised_to_answer(bridge, claude_voice, monkeypatch):
    """A turn waits up to ASK_SECONDS for the session, and the call gave up after ten."""
    monkeypatch.setattr(sessions, "CALL_SECONDS", 0.5)
    monkeypatch.setattr(server, "ASK_SECONDS", 2)
    claude_voice.slow = 1.0
    say(bridge, "snakk med build-7c")
    assert say(bridge, "kjør testene") == "The tests pass."


def test_a_turn_to_a_session_says_who_is_speaking_and_that_the_answer_is_read_aloud(bridge, claude_voice):
    """Spoken to by voice, a session saw a bare sentence from a courier with a made-up name."""
    bridge.remember("You", "hvilke økter kjører nå")
    bridge.remember("It said", "Tre økter kjører, blant dem build-7c.")
    say(bridge, "snakk med build-7c")
    say(bridge, "spør den hva som skjer")
    message = next(a for n, a in claude_voice.called if n == "ask_active_session")["message"]
    assert message.startswith("Her kommer en melding fra Roy gjennom stemme-appen.")
    assert "lest høyt" in message
    assert "Ikke bruk SendMessage tilbake" in message
    assert "samtalepartner" in message
    assert "hvilke økter kjører nå" in message
    assert message.endswith("«spør den hva som skjer»")


def test_only_the_answer_to_the_turn_is_spoken_not_what_the_session_was_busy_with(bridge, claude_voice):
    """A busy session's reply held two thousand characters of other work, with a table."""
    claude_voice.answer = {
        "status": "answered",
        "reply": "Først testene.\n| Del | Hva |\n|---|---|\n| a | b |\nAkkurat nå tester jeg appen din.",
        "turns": [
            {"index": 7, "role": "assistant", "text": "Først testene.\n| Del | Hva |\n|---|---|\n| a | b |"},
            {"index": 8, "role": "user", "text": "Her kommer en melding fra Roy"},
            {"index": 9, "role": "assistant", "text": "Akkurat nå tester jeg **appen** din."},
        ],
    }
    say(bridge, "snakk med build-7c")
    assert say(bridge, "hva gjør du") == "Akkurat nå tester jeg appen din."


def test_a_session_still_working_is_not_quoted_until_it_has_answered(bridge, claude_voice):
    """A busy session's latest words were read out as the answer, three times over."""
    say(bridge, "snakk med build-7c")
    claude_voice.answer = {"status": "still_working", "reply": "Jeg står i mappen din.", "next_after": 4}
    spoken = say(bridge, "hva holder du på med")
    assert "mappen" not in spoken
    assert "build-7c" in spoken


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


def test_a_session_claude_voice_runs_itself_cannot_be_chosen_yet(bridge):
    """Spoken to twice, it never received a word: those are reached another way."""
    spoken = say(bridge, "snakk med runner-1a")
    assert bridge.chosen == target.Target("hermes")
    assert "runner-1a" in spoken


def test_a_turn_the_voice_keeps_is_handed_back_to_it_quietly(bridge):
    """The refusal "Nothing is passed on" was read aloud eight times in one conversation."""
    say(bridge, "snakk med stemmen")
    say(bridge, "hva synes du om været")
    assert bridge.quiet
    say(bridge, "snakk med hermes")
    assert not bridge.quiet


def test_a_long_answer_is_finished_when_the_session_itself_says_it_is_idle(bridge, claude_voice):
    say(bridge, "snakk med build-7c")
    claude_voice.active = [s for s in claude_voice.active if s["name"] != "build-7c"] + [
        {"name": "build-7c", "project": "akso/hydropower", "status": "busy", "kind": "interactive"}
    ]
    claude_voice.answer = {"status": "still_working", "reply": "", "next_after": 4}
    say(bridge, "kjør alt")
    spoken, done = server.keep_waiting(bridge.following, bridge.gateway_url, bridge=bridge, patience=1)
    assert (spoken, done) == ("Done now.", True)


def test_a_session_that_moved_hands_the_conversation_to_where_it_went(bridge, claude_voice):
    """The old window of a continued conversation takes messages and never answers."""
    say(bridge, "snakk med build-7c")
    claude_voice.answer = {"status": "moved", "moved_to": {"id": "c3", "name": "notes-9f"}}
    spoken = say(bridge, "hei")
    assert bridge.chosen == target.Target("session", "notes-9f")
    assert "notes-9f" in spoken


def test_a_message_the_session_never_took_is_said_to_be_lost(bridge, claude_voice):
    say(bridge, "snakk med build-7c")
    claude_voice.answer = {"status": "not_received"}
    spoken = say(bridge, "hei")
    assert "did not get" in spoken
    assert bridge.following is None


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
        # runner-1a is run by claude-voice itself, and cannot be chosen yet.
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


def test_the_page_tells_the_voice_who_it_speaks_for_when_that_changes():
    page = server.PAGE.read_text()
    assert "body.steer !== steered" in page


def test_the_page_matches_an_acknowledgement_by_the_id_it_sent():
    """Every answer was marked lost and said twice: the id comes back as client_event_id."""
    page = server.PAGE.read_text()
    assert "acknowledged(event.client_event_id" in page


def test_something_said_outside_a_delegation_goes_as_an_instruction():
    """A commentary or thinking append needs a delegation; news and approvals have none."""
    page = server.PAGE.read_text()
    assert '"session.instructions.append"' in page
    assert "delegationId == null" in page
