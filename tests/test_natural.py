"""A conversation that feels natural: what the voice is told, and what each turn costs.

Research behind it: references/voice-ux-research.md. gpt-live-1 has no setting for
when a person has finished speaking or for being interrupted; its prompt is the
only lever, in the three parts the vendor says to keep.
"""

import json
import threading
import urllib.request

import pytest

from voice_bridge import budget, live, metrics, server


@pytest.fixture
def bridge(url, tmp_path):
    running = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    yield running
    running.server_close()


@pytest.mark.parametrize("language", ["nb", "en"])
def test_the_voice_is_told_how_to_acknowledge_be_interrupted_and_hand_work_on(language):
    told = live.instructions(language)
    for part in live.POLICIES[language]:
        assert part in told


def test_the_voice_keeps_listening_while_somebody_thinks_and_never_repeats_itself():
    told = live.instructions("nb")
    assert "Lytt videre" in told
    assert "samme formulering" in told


def test_the_holding_hint_is_a_fact_to_know_not_a_line_to_say():
    """The hint "Si kort at du setter i gang, og vent" was read out word for word."""
    assert not live.holding("nb").startswith("Si ")
    assert "ingenting er ferdig" in live.holding("nb")


def test_each_stage_of_a_turn_is_timed(bridge):
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{bridge.server_port}/timing",
            data=json.dumps({"bridge_ms": 120, "acknowledged_ms": 30, "first_words_ms": 900}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=10).read()
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
    stages = {r["name"]: r["ms"] for r in bridge.store.rows("stage")}
    assert stages == {"bridge": 120, "acknowledged": 30, "first_words": 900}
    assert metrics.summary(bridge.store)["stages"]["first_words"]["this_week"]["p50_ms"] == 900


def test_a_failure_is_said_plainly_with_what_happens_next():
    """It said "The bridge did not answer: Failed to fetch" and stopped there."""
    page = server.PAGE.read_text()
    assert "did not answer:" not in page
    assert "could not do that:" not in page
    assert "FAILED_PLAINLY" in page
    assert "try again" in page


def test_the_page_reports_how_long_each_stage_of_a_turn_took():
    page = server.PAGE.read_text()
    assert 'fetch("/timing"' in page
    assert "first_words_ms" in page


def test_how_long_a_session_takes_to_open_is_kept(bridge):
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{bridge.server_port}/timing",
            data=json.dumps({"opened_ms": 1800}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=10).read()
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
    assert {r["name"]: r["ms"] for r in bridge.store.rows("stage")} == {"opened": 1800}


def test_the_page_never_jumps_to_the_newest_line_while_somebody_reads_further_up():
    """Scrolled up to read, every new word threw the page back to the bottom."""
    page = server.PAGE.read_text()
    assert page.count("scrollIntoView") == 1  # the tabs, which only move when tapped
    assert "follow(log, following)" in page
    assert "follow(under, following)" in page
