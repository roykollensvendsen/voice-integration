"""What must interrupt is pushed: to the phone, and as news. ADR-VI-031."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from voice_bridge import alerts, budget, metrics, server


class _Ntfy(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.server.pushed.append((self.path, self.headers.get("Title"), self.rfile.read(length).decode()))
        self.send_response(200)
        self.end_headers()


@pytest.fixture
def ntfy():
    running = HTTPServer(("127.0.0.1", 0), _Ntfy)
    running.pushed = []
    thread = threading.Thread(target=running.serve_forever, daemon=True)
    thread.start()
    yield running
    running.shutdown()
    running.server_close()


@pytest.fixture
def bridge(url, tmp_path):
    running = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    yield running
    running.server_close()


def watcher(bridge, ntfy, **limits):
    where = f"http://127.0.0.1:{ntfy.server_port}"
    return alerts.Watcher(bridge, server=where, topic="voice-bridge-test", **limits)


def test_low_memory_is_pushed_to_the_phone_and_told_as_news(bridge, ntfy):
    watch = watcher(bridge, ntfy, memory_mb=10**9)
    watch.check()
    assert ntfy.pushed[0][0] == "/voice-bridge-test"
    assert "memory" in ntfy.pushed[0][1].lower() or "minne" in ntfy.pushed[0][2].lower()
    told = [e for e in bridge.watching if e["event"] == "claude.news"]
    assert told[-1]["aloud"]


def test_the_same_cause_raises_at_most_one_alert_per_quiet_seconds(bridge, ntfy):
    watch = watcher(bridge, ntfy, memory_mb=10**9)
    watch.check()
    watch.check()
    assert len(ntfy.pushed) == 1


def test_a_start_after_an_automatic_restart_is_alerted(bridge, ntfy):
    metrics.started(bridge.store, restarts_now=1)
    metrics.started(bridge.store, restarts_now=2)
    watcher(bridge, ntfy, memory_mb=0).check()
    assert any("startet på nytt" in (title or "") for _, title, _ in ntfy.pushed)


def test_a_burst_of_failures_is_alerted(bridge, ntfy):
    for _ in range(3):
        bridge.store.record("tool", "ask_active_session", ok=False, detail="boom")
    watcher(bridge, ntfy, memory_mb=0, errors=3).check()
    assert any("fail" in (title or "").lower() or "feil" in body for _, title, body in ntfy.pushed)


def test_without_a_topic_nothing_is_pushed_but_the_news_still_comes(bridge):
    watch = alerts.Watcher(bridge, server="http://127.0.0.1:9", topic="", memory_mb=10**9)
    watch.check()
    assert [e for e in bridge.watching if e["event"] == "claude.news"]


def test_an_alert_raised_long_ago_may_be_raised_again(bridge, ntfy):
    watch = watcher(bridge, ntfy, memory_mb=10**9)
    watch.check()
    watch.last["memory"] = time.monotonic() - alerts.QUIET_SECONDS - 1
    watch.check()
    assert len(ntfy.pushed) == 2


def test_alert_settings_are_read_from_their_own_file(tmp_path):
    env = tmp_path / "env"
    env.write_text("NTFY_TOPIC=abc\nNTFY_SERVER=https://example.org\n")
    assert alerts.settings(env, {}) == ("https://example.org", "abc")
    assert alerts.settings(tmp_path / "none", {}) == (alerts.DEFAULT_SERVER, "")
    assert json.dumps(alerts.settings(env, {"NTFY_TOPIC": "env"})) == json.dumps(
        ["https://example.org", "env"]
    )
