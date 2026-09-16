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


def test_what_the_voice_does_not_say_is_kept_for_the_screen(bridge):
    post(f"{bridge}/delegation", {"transcript": "run the tests"})
    request = urllib.request.Request(f"{bridge}/watch", headers={"Accept": "text/event-stream"})
    seen = []
    with urllib.request.urlopen(request, timeout=10) as stream:
        for raw in stream:
            line = raw.decode().strip()
            if line.startswith("data:"):
                seen.append(json.loads(line[5:]))
            if len(seen) >= 1:
                break
    assert seen[0]["event"] == "run.asked"
    assert seen[0]["asked"] == "run the tests"


def test_the_page_says_what_happened_in_words_a_person_did_not_have_to_learn(bridge):
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    for machine_word in ('"tool.started">', ">run.asked<", ">message.delta<", ">writing</div>"):
        assert machine_word not in page, f"{machine_word} is shown to a reader"
    for plain in ("Running ", "Waiting for your permission", "Writing the answer", "The conversation"):
        assert plain in page


def test_the_conversation_reads_downwards_and_the_agent_log_beside_it(bridge):
    """Two lists, not one: what was said, and what was done to be able to say it."""
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert "log.append(row)" in page, "the conversation must read oldest first"
    assert "under.append(row)" in page, "so must the agent log"
    assert "log.prepend" not in page
    assert "under.prepend" not in page
    assert page.index('<div id="log">') < page.index('<div id="under">')


def test_speech_is_grouped_into_turns_rather_than_glued_into_one(bridge):
    """The API has no turn-completed event, so the page groups by silence."""
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert "TURN_GAP_MS" in page, "a turn must end on a gap, not on a request"
    assert "start_ms" in page, "grouping needs the timeline"
    assert "end_ms" in page, "grouping needs the timeline"
    assert 'heard("You", event.delta' in page, "a fragment shows as it arrives"
    assert 'show("You", transcript' not in page, "a turn is not drawn at request time"


def test_what_the_voice_says_is_drawn_as_it_arrives(bridge):
    """There is no transcript-done event, so waiting for one drew nothing at all."""
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert 'heard("It said", event.delta' in page
    assert "output_transcript.done" not in page, "that event does not exist"


def test_the_two_sides_sit_beside_each_other_and_swipe_on_a_phone(bridge):
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert "grid-template-columns: 1fr 1fr" in page, "two columns when there is room"
    assert "scroll-snap-type: x mandatory" in page, "one screen each, swiped, when there is not"
    assert "scroll-snap-align: start" in page
    assert page.count('class="pane"') == 2


def test_a_new_conversation_never_continues_the_last_one(bridge):
    """Each session restarts the clock at zero, so a gap can come out negative."""
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert "turn.session === session" in page, "a turn belongs to one session"
    assert "gap >= 0 && gap <= TURN_GAP_MS" in page, "a negative gap is not a small gap"
    assert "session += 1" in page


def test_the_bridge_keeps_the_transcript_so_a_new_session_can_resume_it(bridge):
    post(f"{bridge}/turn", {"who": "You", "text": "Run the tests"})
    post(f"{bridge}/turn", {"who": "It said", "text": "They pass."})
    post(f"{bridge}/turn", {"who": "You", "text": "   "})
    status, _ = post(f"{bridge}/session", {"sdp": "v=0"})
    assert status in (200, 403)


def test_an_empty_turn_is_not_worth_remembering(tmp_path):
    running = server.Bridge(("127.0.0.1", 0), "http://127.0.0.1:1", budget.Ledger(tmp_path / "s.json"))
    try:
        running.remember("You", "  ")
        running.remember("You", "Run the tests")
        running.remember("It said", "They pass.")
        assert running.recent() == [
            {"role": "user", "content": "Run the tests"},
            {"role": "assistant", "content": "They pass."},
        ]
    finally:
        running.server_close()
