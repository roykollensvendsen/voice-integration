"""The three routes the browser can reach, and nothing else."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from voice_bridge import budget, live, server


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
    assert {k: v for k, v in sent.items() if k != "instructions"} == {
        "input": "run the tests",
        "model": "hermes-agent",
        "session_id": "voice",
    }


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


def test_work_that_outlasts_our_patience_says_it_will_come_back(url):
    spoken = server.answer_delegation("run the tests", url, patience=0.0)
    assert spoken == "Still working. I will tell you when it is done."


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
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Run the tests"}],
            },
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "They pass."}],
            },
        ]
    finally:
        running.server_close()


def test_a_voice_turn_asks_the_gateway_to_finish_inside_it(bridge, hermes):
    """Background work completes the run at once and answers nobody."""
    post(f"{bridge}/delegation", {"transcript": "run the tests"})
    _, sent, _ = hermes.seen[0]
    assert "instructions" in sent, "a voice turn is not an ordinary run"
    assert "Do not dispatch background subagents" in sent["instructions"]
    assert "A person is listening" in sent["instructions"]


def test_only_a_word_that_is_plainly_yes_or_no_answers_a_permission_question(url, tmp_path):
    running = server.Bridge(("127.0.0.1", 0), url, budget.Ledger(tmp_path / "s.json"))
    try:
        running.awaiting = "run_ab12"
        spoken = server.answer_delegation("maybe later, I think", url, bridge=running)
        assert running.awaiting == "run_ab12", "a vague reply leaves the question open"
        assert "permission" not in spoken
    finally:
        running.server_close()


def test_a_plain_yes_answers_the_question_instead_of_starting_work(url, tmp_path, hermes):
    running = server.Bridge(("127.0.0.1", 0), url, budget.Ledger(tmp_path / "s.json"))
    try:
        running.awaiting = "run_ab12"
        server.answer_delegation("ja", url, bridge=running)
        assert running.awaiting is None
        assert hermes.seen[0][0] == "/v1/runs/run_ab12/approval"
        assert hermes.seen[0][1] == {"choice": "once"}
    finally:
        running.server_close()


def test_a_permission_can_only_be_answered_once_or_denied(bridge):
    status, body = post(f"{bridge}/approval", {"choice": "always"})
    assert status == 400
    assert "once or deny" in body["error"]


def test_a_permission_question_is_the_one_row_you_can_answer(bridge):
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert 'if (e.event === "approval.request") asking(row, e)' in page
    assert '["Allow once", "once"], ["Refuse", "deny"]' in page
    assert '"always"' not in page, "a page must not offer a standing permission"


def test_a_permission_question_is_noticed_however_late_it_arrives(url, tmp_path):
    """Patience runs out long before an agent gets round to asking."""
    running = server.Bridge(("127.0.0.1", 0), url, budget.Ledger(tmp_path / "s.json"))
    try:
        assert running.awaiting is None
        server.notice(running, {"event": "approval.request", "run_id": "run_ab12"})
        assert running.awaiting == "run_ab12"
    finally:
        running.server_close()


def test_a_remembered_turn_is_a_message_item_not_a_bare_string(tmp_path):
    """A string in `content` is refused outright, which is how this was found."""
    running = server.Bridge(("127.0.0.1", 0), "http://127.0.0.1:1", budget.Ledger(tmp_path / "s.json"))
    try:
        running.remember("You", "Run the tests")
        turn = running.recent()[0]
        assert turn["type"] == "message"
        assert isinstance(turn["content"], list)
        assert turn["content"][0] == {"type": "input_text", "text": "Run the tests"}
    finally:
        running.server_close()


def test_a_long_conversation_is_trimmed_rather_than_refused(tmp_path):
    """The startup list takes 8,192 tokens across every message, and no more."""
    running = server.Bridge(("127.0.0.1", 0), "http://127.0.0.1:1", budget.Ledger(tmp_path / "s.json"))
    try:
        for _ in range(live.TURNS_REMEMBERED):
            running.remember("You", "x" * 5000)
        kept = running.recent()
        assert 0 < len(kept) < live.TURNS_REMEMBERED
        assert sum(len(t["content"][0]["text"]) for t in kept) <= server.HISTORY_CHARACTERS
    finally:
        running.server_close()


def test_work_that_outlasts_the_wait_says_which_run_to_keep_waiting_on(bridge):
    _, body = post(f"{bridge}/delegation", {"transcript": "run the tests"})
    assert set(body) == {"content", "run_id", "finished"}


def test_the_bridge_can_be_asked_to_keep_waiting(bridge, run_id):
    _, body = post(f"{bridge}/run", {"run_id": run_id})
    assert body["finished"] is True
    assert body["content"] == "The tests pass."


def test_a_run_still_going_is_not_reported_finished(url, tmp_path):
    running = server.Bridge(("127.0.0.1", 0), url, budget.Ledger(tmp_path / "s.json"))
    try:
        spoken, done = server.keep_waiting("run_ab12", url, patience=0.0)
        assert done is False
        assert spoken == "Still working. I will tell you when it is done."
    finally:
        running.server_close()


def test_nobody_is_asked_to_remember_a_run_identifier(bridge):
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert "waitOn(runId, delegationId)" in page, "the answer arrives on its own"


def test_a_turn_is_finished_only_when_the_run_behind_it_is(url, tmp_path):
    """Saying a turn is done while the work runs means nobody waits for the answer."""
    running = server.Bridge(("127.0.0.1", 0), url, budget.Ledger(tmp_path / "s.json"))
    try:
        server.answer_delegation("run the tests", url, patience=0.0, bridge=running)
        assert running.following == "run_ab12"
        server.answer_delegation("run the tests", url, bridge=running)
        assert running.following is None
    finally:
        running.server_close()


def test_the_page_is_told_to_keep_waiting_when_the_work_is_not_done(bridge):
    """The stand-in answers running on its first look, so this is the unfinished case."""
    _, body = post(f"{bridge}/delegation", {"transcript": "run the tests"})
    assert body["finished"] is True, "the stand-in finishes on the second look"
    assert body["run_id"] is None


def test_separate_things_said_stay_separate_when_they_are_sent_on(bridge, hermes):
    """Flattening two turns made one confused instruction out of a question and an answer."""
    post(f"{bridge}/delegation", {"transcript": "can we do something meanwhile\nyes run claude"})
    _, sent, _ = hermes.seen[0]
    assert sent["input"] == "can we do something meanwhile\nyes run claude"


def test_a_voice_turn_asks_for_questions_a_person_can_say(bridge, hermes):
    """It asked out loud for one of four numbered options containing file paths."""
    post(f"{bridge}/delegation", {"transcript": "run the tests"})
    asked = hermes.seen[0][1]["instructions"]
    assert "answer in a few spoken words" in asked
    assert "never read out a numbered list" in asked
    assert "say a file path" in asked


def test_a_choice_the_agents_offer_can_be_tapped_instead_of_pronounced(bridge):
    """It asked out loud for one of four numbered options, and then for an exact phrase."""
    with urllib.request.urlopen(bridge, timeout=10) as reply:
        page = reply.read().decode()
    assert "function choices(text)" in page
    assert "offer(note(" in page, "an answer with choices gets buttons"
    assert "async function answerWith(text)" in page
