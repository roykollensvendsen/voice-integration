"""Nothing worth saying is lost while the microphone is down. ADR-VI-029."""

import json
import threading
import time
import urllib.request

import pytest
from conftest import NEWS

from voice_bridge import budget, live, server


@pytest.fixture
def bridge(url, tmp_path):
    running = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    yield running
    running.server_close()


def post(where, payload):
    request = urllib.request.Request(
        where, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=10) as reply:
        return json.loads(reply.read())


def serving(bridge):
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{bridge.server_port}", thread


def test_news_that_was_not_heard_is_said_when_the_microphone_is_taken_again(bridge, monkeypatch):
    monkeypatch.setattr(live, "open_session", lambda *_a, **_k: "v=0")
    bridge.hear(NEWS)
    where, thread = serving(bridge)
    try:
        missed = post(f"{where}/session", {"sdp": "v=0"})["missed"]
        assert "build finished" in missed
        assert "Yes or no?" in missed
        assert "notes is working" not in missed
        post(f"{where}/heard", {"seq": 3})
        assert post(f"{where}/session", {"sdp": "v=0"})["missed"] == ""
    finally:
        bridge.shutdown()
        thread.join(timeout=5)


def test_a_long_absence_is_counted_rather_than_read_out_in_full(bridge):
    bridge.hear([{"session": f"s{i}", "kind": "finished", "text": f"s{i} finished."} for i in range(9)])
    missed = bridge.missed()
    assert "s8 finished." in missed
    assert "s0 finished." not in missed
    assert str(9 - server.MISSED_SPOKEN) in missed


def test_the_same_news_is_said_once_while_you_were_away(bridge):
    """The welcome back read the same sentence six times over."""
    bridge.hear([{"session": "x", "kind": "finished", "text": "x has finished and is waiting."}] * 6)
    assert bridge.missed().count("x has finished") == 1


def test_news_about_the_session_you_are_talking_to_is_not_read_out(bridge):
    """Every turn of the chosen session ends in "has finished", and that is not news."""
    bridge.chosen = server.target.Target("session", "x")
    bridge.hear([{"session": "x", "kind": "finished", "text": "x has finished and is waiting."}])
    told = [e for e in bridge.watching if e["event"] == "claude.news"]
    assert not told[-1]["aloud"]
    assert bridge.missed() == ""


def test_the_place_in_the_news_survives_a_restart(bridge, url, tmp_path):
    bridge.hear(NEWS)
    bridge.placed_in_news("b42.f7")
    again = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    try:
        assert again.cursor == "b42.f7"
        assert "build finished" in again.missed()
    finally:
        again.server_close()


def test_an_answer_nobody_waited_for_becomes_news(bridge):
    bridge.polled["run_old"] = time.monotonic() - server.UNWATCHED_SECONDS - 1
    bridge.run_finished("run_old", "The tests pass.")
    told = [e for e in bridge.watching if e["event"] == "claude.news"]
    assert told[-1]["aloud"]
    assert "The tests pass." in told[-1]["said"]
    assert "The tests pass." in bridge.missed()


def test_an_answer_somebody_is_waiting_for_is_not_told_twice(bridge):
    bridge.polled["run_new"] = time.monotonic()
    bridge.run_finished("run_new", "The tests pass.")
    assert [e for e in bridge.watching if e["event"] == "claude.news"] == []


def test_a_page_that_stops_waiting_says_so_aloud_and_reports_what_it_said():
    page = server.PAGE.read_text()
    assert "will come as news" in page
    assert 'fetch("/heard"' in page
    assert "body.missed" in page
