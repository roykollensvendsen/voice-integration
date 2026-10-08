"""Every turn traced and measured, and kept long enough to compare weeks.

The bridge was stopped for lack of memory once, and the page answered 502 until
somebody noticed. Every problem since was found by somebody hearing it go wrong.
So each spoken turn gets a trace id that follows it into claude-voice; each
event is one JSON line in the log; and a few numbers are kept in SQLite, from
the standard library, for long enough to say whether this week went better than
the last. ADR-VI-031.

Nothing here holds what was said: names, timings and outcomes only.
"""

from __future__ import annotations

import contextlib
import contextvars
import datetime as dt
import json
import pathlib
import secrets
import sqlite3
import sys
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

#: How many days of measurements are kept.
KEPT_DAYS = 90

#: How long a trace id is, in hex characters: short enough to read, long enough
#: never to collide within a day.
TRACE_LENGTH = 12

WEEK = 7 * 86400

#: The turn being handled on this thread, if any.
TRACE: contextvars.ContextVar[str] = contextvars.ContextVar("trace", default="")


def new_trace() -> str:
    """A trace id for one spoken turn."""
    return secrets.token_hex(TRACE_LENGTH // 2)


@contextlib.contextmanager
def tracing(trace: str) -> Iterator[str]:
    """Everything measured inside this belongs to `trace`."""
    token = TRACE.set(trace)
    try:
        yield trace
    finally:
        TRACE.reset(token)


class Store:
    """The measurements, in one SQLite file, pruned to KEPT_DAYS on opening."""

    def __init__(self, path: pathlib.Path | None) -> None:
        """Open, or create, the store at `path`; None keeps it in memory."""
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.db = sqlite3.connect(str(path) if path else ":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.lock, self.db:
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS events (at REAL, event TEXT, name TEXT, ms REAL,"
                " ok INTEGER, trace TEXT, detail TEXT)"
            )
            self.db.execute("CREATE INDEX IF NOT EXISTS events_at ON events (event, at)")
            # RULE: measurements are kept for KEPT_DAYS and no longer
            self.db.execute("DELETE FROM events WHERE at < ?", (time.time() - KEPT_DAYS * 86400,))

    def record(  # noqa: PLR0913 — one row has this many columns
        self,
        event: str,
        name: str,
        *,
        ms: float | None = None,
        ok: bool = True,
        detail: str = "",
        at: float | None = None,
    ) -> None:
        """Keep one event, and write it to the log as one line."""
        when = time.time() if at is None else at
        trace = TRACE.get()
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (when, event, name, ms, int(ok), trace, detail[:200]),
            )
        line = {"event": event, "name": name, "ok": ok, "trace": trace or "-"}
        if ms is not None:
            line["ms"] = round(ms, 1)
        if detail:
            line["detail"] = detail[:200]
        sys.stdout.write(json.dumps(line, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def rows(self, event: str, since: float = 0.0) -> list[dict[str, Any]]:
        """Every kept event of one kind since `since`, oldest first."""
        with self.lock:
            found = self.db.execute(
                "SELECT * FROM events WHERE event = ? AND at >= ? ORDER BY at", (event, since)
            ).fetchall()
        return [dict(row) for row in found]


@contextlib.contextmanager
def measured(store: Store | None, event: str, name: str) -> Iterator[dict[str, Any]]:
    """Time what happens inside, and keep it; a raised error is kept as a failure."""
    started = time.monotonic()
    outcome: dict[str, Any] = {"ok": True, "detail": ""}
    try:
        yield outcome
    except Exception as failure:
        outcome.update(ok=False, detail=str(failure))
        raise
    finally:
        if store is not None:
            ms = (time.monotonic() - started) * 1000
            store.record(event, name, ms=ms, ok=outcome["ok"], detail=str(outcome["detail"]))


def started(store: Store, restarts_now: int | None) -> str:
    """Record that the bridge started, and whether systemd had to restart it."""
    last = store.rows("restarts")
    before = int(last[-1]["detail"]) if last and str(last[-1]["detail"]).isdigit() else None
    why = (
        "auto-restart"
        if restarts_now is not None and before is not None and restarts_now > before
        else "start"
    )
    if restarts_now is not None:
        with store.lock, store.db:
            store.db.execute(
                "INSERT INTO events VALUES (?, 'restarts', 'systemd', NULL, 1, '', ?)",
                (time.time(), str(restarts_now)),
            )
    store.record("start", why)
    return why


def _week(rows: list[dict[str, Any]]) -> dict[str, Any]:
    times = sorted(r["ms"] for r in rows if r["ms"] is not None)
    middle = times[len(times) // 2] if times else None
    slow = times[max(0, int(len(times) * 0.95) - 1)] if times else None
    return {
        "calls": len(rows),
        "errors": sum(1 for r in rows if not r["ok"]),
        "p50_ms": round(middle) if middle is not None else None,
        "p95_ms": round(slow) if slow is not None else None,
    }


def _by_name(rows: list[dict[str, Any]], now: float) -> dict[str, dict[str, Any]]:
    names = sorted({r["name"] for r in rows})
    return {
        name: {
            "this_week": _week([r for r in rows if r["name"] == name and r["at"] >= now - WEEK]),
            "last_week": _week(
                [r for r in rows if r["name"] == name and now - 2 * WEEK <= r["at"] < now - WEEK]
            ),
        }
        for name in names
    }


def summary(store: Store, now: float | None = None) -> dict[str, Any]:
    """How the bridge is doing: now, what failed lately, and this week against the last."""
    at = time.time() if now is None else now
    since = at - 2 * WEEK
    starts = store.rows("start", since)
    failures = [r for event in ("tool", "turn") for r in store.rows(event, since) if not r["ok"]]
    failures.sort(key=lambda r: r["at"], reverse=True)
    return {
        "now": {
            "up_since": _iso(starts[-1]["at"]) if starts else None,
            "last_start": starts[-1]["name"] if starts else None,
        },
        "restarts": {
            "this_week": sum(1 for r in starts if r["name"] == "auto-restart" and r["at"] >= at - WEEK),
            "last_week": sum(1 for r in starts if r["name"] == "auto-restart" and r["at"] < at - WEEK),
        },
        "turns": _by_name(store.rows("turn", since), at),
        "tools": _by_name(store.rows("tool", since), at),
        "cut": {
            "this_week": sum(1 for r in store.rows("cut", at - WEEK)),
            "last_week": len(store.rows("cut", since)) - len(store.rows("cut", at - WEEK)),
        },
        "errors": [
            {
                "at": _iso(r["at"]),
                "event": r["event"],
                "name": r["name"],
                "trace": r["trace"],
                "error": r["detail"],
            }
            for r in failures[:10]
        ],
    }


def memory() -> dict[str, int]:
    """How much memory this process uses, and how much the machine has left."""
    found: dict[str, int] = {}
    try:
        for line in pathlib.Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                found["rss_mb"] = int(line.split()[1]) // 1024
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            key, _, value = line.partition(":")
            if key in ("MemAvailable", "MemTotal"):
                found["available_mb" if key == "MemAvailable" else "total_mb"] = int(value.split()[0]) // 1024
    except OSError:
        pass
    return found


def spoken(summary: dict[str, Any]) -> str:
    """The summary as two or three sentences somebody can listen to."""
    now = summary.get("now") or {}
    restarts = summary.get("restarts") or {}
    turns = [w["this_week"] for w in (summary.get("turns") or {}).values()]
    times = [t["p50_ms"] for t in turns if t.get("p50_ms") is not None]
    failed = sum(t["errors"] for t in turns) + sum(
        w["this_week"]["errors"] for w in (summary.get("tools") or {}).values()
    )
    said = [f"Broen har gått siden {_said_when(now.get('up_since'))}."]
    said.append(
        f"Den har hatt {restarts.get('this_week', 0)} automatiske omstarter denne uka, "
        f"mot {restarts.get('last_week', 0)} uka før."
    )
    if times:
        said.append(f"Et svar tar vanligvis rundt {round(max(times) / 1000, 1)} sekunder.")
    said.append(f"{failed} feil denne uka." if failed else "Ingen feil denne uka.")
    return " ".join(said)


MONTHS = (
    "januar",
    "februar",
    "mars",
    "april",
    "mai",
    "juni",
    "juli",
    "august",
    "september",
    "oktober",
    "november",
    "desember",
)


def _said_when(iso: str | None) -> str:
    """A moment as somebody would say it: "klokka 11:37 i dag", not an ISO timestamp."""
    if not iso:
        return "en ukjent tid"
    when = dt.datetime.fromisoformat(iso).astimezone()
    today = dt.datetime.now().astimezone().date()
    if when.date() == today:
        return f"klokka {when:%H:%M} i dag"
    return f"klokka {when:%H:%M} den {when.day}. {MONTHS[when.month - 1]}"


def _iso(at: float) -> str:
    return dt.datetime.fromtimestamp(at, dt.UTC).isoformat(timespec="seconds")
