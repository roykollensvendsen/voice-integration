"""Every turn is traced and measured, and kept long enough to compare weeks. ADR-VI-031."""

import json
import threading
import time
import urllib.request

import pytest
from conftest import TOKEN

from voice_bridge import budget, metrics, server, sessions
from voice_bridge.policy import Refused


@pytest.fixture
def store(tmp_path):
    return metrics.Store(tmp_path / "metrics.sqlite")


@pytest.fixture
def client(claude_voice, store):
    return sessions.Client(f"http://127.0.0.1:{claude_voice.server_port}/mcp", TOKEN, store=store)


def test_a_tool_call_carries_the_turns_trace_id(client, claude_voice):
    with metrics.tracing("ab12cd34ef56"):
        client.call("whats_new", {"cursor": "b1.f0"})
    assert claude_voice.metas[-1] == {"trace_id": "ab12cd34ef56"}


def test_a_tool_call_is_measured(client, store):
    client.call("whats_new", {"cursor": "b1.f0"})
    rows = store.rows("tool")
    assert [(r["name"], r["ok"]) for r in rows] == [("whats_new", 1)]
    assert rows[0]["ms"] >= 0


def test_a_failing_tool_call_is_counted_as_an_error(client, store):
    with pytest.raises(Refused):
        client.call("approve", {"approval_id": "99"})
    assert [(r["name"], r["ok"]) for r in store.rows("tool")] == [("approve", 0)]
    assert "expired" in store.rows("tool")[0]["detail"]


def test_every_spoken_turn_is_traced_and_measured(url, tmp_path):
    bridge = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        where = f"http://127.0.0.1:{bridge.server_port}/delegation"
        for said in ("hva er klokka", "hva er klokka"):
            request = urllib.request.Request(
                where,
                data=json.dumps({"transcript": said}).encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(request, timeout=10).read()
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
        bridge.server_close()
    turns = bridge.store.rows("turn")
    assert [t["name"] for t in turns] == ["hermes", "hermes"]
    assert all(t["ms"] >= 0 for t in turns)
    assert turns[0]["trace"] != turns[1]["trace"]
    assert len(turns[0]["trace"]) == metrics.TRACE_LENGTH


def test_measurements_are_kept_for_kept_days_and_no_longer(tmp_path):
    first = metrics.Store(tmp_path / "metrics.sqlite")
    first.record("tool", "whats_new", at=time.time() - (metrics.KEPT_DAYS + 1) * 86400)
    first.record("tool", "whats_new")
    again = metrics.Store(tmp_path / "metrics.sqlite")
    assert len(again.rows("tool")) == 1


def test_a_start_after_an_automatic_restart_is_recorded_as_one(store):
    assert metrics.started(store, restarts_now=2) == "start"
    assert metrics.started(store, restarts_now=3) == "auto-restart"
    assert [r["name"] for r in store.rows("start")] == ["start", "auto-restart"]


def test_each_event_is_one_json_line(store, capsys):
    with metrics.tracing("feedfacecafe"):
        store.record("tool", "whats_new", ms=12.5)
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["event"] == "tool"
    assert line["name"] == "whats_new"
    assert line["trace"] == "feedfacecafe"


def test_the_summary_compares_this_week_with_the_last(store):
    now = time.time()
    for days_ago, ok in ((1, 1), (2, 0), (9, 1), (10, 1)):
        store.record(
            "tool", "ask_active_session", ms=100.0 * (days_ago + 1), ok=bool(ok), at=now - days_ago * 86400
        )
    week = metrics.summary(store, now=now)["tools"]["ask_active_session"]
    assert week["this_week"]["calls"] == 2
    assert week["this_week"]["errors"] == 1
    assert week["last_week"]["calls"] == 2
    assert week["last_week"]["errors"] == 0
