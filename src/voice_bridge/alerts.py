"""What must interrupt is pushed, because nobody asks a failing bridge how it is.

The bridge was once stopped for lack of memory, and the page answered 502 until
somebody happened to look. The alerts that matter fire when nobody is in a voice
session, so each one goes to the person's phone through ntfy, and is told as
news as well, for the voice and the page. ADR-VI-031.
"""

from __future__ import annotations

import os
import pathlib
import threading
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from voice_bridge import metrics

if TYPE_CHECKING:
    from voice_bridge.server import Bridge

#: How often the watcher looks.
CHECK_SECONDS = 30.0

#: Below this much available memory, the machine is close to stopping things.
MEMORY_MB = 1500

#: This many failed calls or turns within the window is a burst worth hearing of.
ERRORS_PER_WINDOW = 5
WINDOW_SECONDS = 600

#: The same cause raises at most one alert in this long.
QUIET_SECONDS = 3600

DEFAULT_SERVER = "https://ntfy.sh"
ENV_FILE = pathlib.Path.home() / ".config" / "voice-bridge" / "env"
PUSH_SECONDS = 10.0


def settings(env_file: pathlib.Path = ENV_FILE, environ: dict[str, str] | None = None) -> tuple[str, str]:
    """The ntfy server and topic: the environment first, then the bridge's own file."""
    found: dict[str, str] = {}
    try:
        for line in env_file.read_text().splitlines():
            name, _, value = line.partition("=")
            found[name.strip()] = value.strip().strip("\"'")
    except OSError:
        pass
    found.update(
        {k: v for k, v in (os.environ if environ is None else environ).items() if k.startswith("NTFY_")}
    )
    return found.get("NTFY_SERVER") or DEFAULT_SERVER, found.get("NTFY_TOPIC", "")


class Watcher:
    """Looks at the bridge's own numbers, and raises an alert when one crosses a line."""

    def __init__(
        self,
        bridge: Bridge,
        *,
        server: str,
        topic: str,
        memory_mb: int = MEMORY_MB,
        errors: int = ERRORS_PER_WINDOW,
    ) -> None:
        """Watch `bridge`, pushing to `topic` on `server` when there is one."""
        self.bridge = bridge
        self.server = server.rstrip("/")
        self.topic = topic
        self.memory_mb = memory_mb
        self.errors = errors
        #: When each cause was last raised, so the same thing is not said every half minute.
        self.last: dict[str, float] = {}
        self.restarts_seen = len([r for r in bridge.store.rows("start") if r["name"] == "auto-restart"])
        self.restarts_seen -= 1 if self.restarts_seen and self._latest_start_was_restart() else 0

    def _latest_start_was_restart(self) -> bool:
        starts = self.bridge.store.rows("start")
        return bool(starts) and starts[-1]["name"] == "auto-restart"

    def check(self) -> None:
        """Look once, and raise whatever needs raising."""
        available = metrics.memory().get("available_mb")
        if available is not None and available < self.memory_mb:
            self.raise_("memory", "Lite minne igjen", f"Maskinen har bare {available} MB ledig minne.")
        restarts = len([r for r in self.bridge.store.rows("start") if r["name"] == "auto-restart"])
        if restarts > self.restarts_seen:
            self.restarts_seen = restarts
            self.raise_(
                "restart", "Broen startet på nytt", "Stemmebroen stoppet og ble startet på nytt automatisk."
            )
        since = time.time() - WINDOW_SECONDS
        failed = [
            r for event in ("tool", "turn") for r in self.bridge.store.rows(event, since) if not r["ok"]
        ]
        if len(failed) >= self.errors:
            self.raise_("errors", "Mange feil i broen", f"{len(failed)} feil de siste ti minuttene.")

    def raise_(self, cause: str, title: str, said: str) -> None:
        """Push one alert and tell it as news, unless the same cause was raised lately."""
        # RULE: the same cause raises at most one alert per QUIET_SECONDS
        if time.monotonic() - self.last.get(cause, -QUIET_SECONDS) < QUIET_SECONDS:
            return
        self.last[cause] = time.monotonic()
        self.bridge.store.record("alert", cause, detail=said)
        self.bridge.hear([{"session": "broen", "kind": "error", "text": said}])
        if self.topic:
            self._push(title, said)

    def _push(self, title: str, said: str) -> None:
        request = urllib.request.Request(  # noqa: S310 — the server comes from the person's own settings
            f"{self.server}/{self.topic}",
            data=said.encode(),
            headers={"Title": title, "Priority": "high", "Tags": "warning"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=PUSH_SECONDS):  # noqa: S310 — as above
                pass
        except (urllib.error.URLError, OSError) as failure:
            self.bridge.store.record("alert", "push", ok=False, detail=str(failure))

    def run(self) -> None:
        """Keep looking, on its own thread, for as long as the bridge runs."""

        def watch() -> None:
            while True:
                try:
                    self.check()
                except Exception as failure:  # noqa: BLE001 — a watcher that dies watches nothing
                    self.bridge.store.record("alert", "watcher", ok=False, detail=str(failure))
                time.sleep(CHECK_SECONDS)

        threading.Thread(target=watch, daemon=True).start()
