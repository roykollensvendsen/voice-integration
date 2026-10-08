"""What is still missing before the page can talk, and the one thing to do about each.

A newcomer, or the assistant setting the bridge up for them, runs `voicebridge
ready` after each step and does the first fix it names. The voice alone needs an
OpenAI key and some budget; the planner and the Claude sessions are each one
more program, and each optional.
"""

from __future__ import annotations

import os
import pathlib
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING

from voice_bridge import sessions

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, MutableMapping

    from voice_bridge.budget import Ledger

#: The bridge's own settings, one NAME=value a line.
SETTINGS = "~/.config/voice-bridge/env"
SETTINGS_FILE = pathlib.Path(SETTINGS).expanduser()
OPENAI_MODELS = "https://api.openai.com/v1/models"
PROBE_SECONDS = 5.0


@dataclass(frozen=True)
class Check:
    """One thing the bridge needs: whether it is there, what was found, and what to do."""

    name: str
    required: bool
    ok: bool
    detail: str
    fix: str = ""


def apply_settings(environ: MutableMapping[str, str], file: pathlib.Path = SETTINGS_FILE) -> None:
    """Fill in from `file` every name the environment does not have, even an empty one."""
    try:
        lines = file.read_text().splitlines()
    except OSError:
        return
    for line in lines:
        name, sep, value = line.partition("=")
        name = name.strip()
        if sep and name and not name.startswith("#") and name not in environ:
            environ[name] = value.strip().strip("\"'")


def http_status(url: str, headers: Mapping[str, str]) -> int:
    """The status `url` answers with, or 0 when nothing answers."""
    request = urllib.request.Request(url, headers=dict(headers))  # noqa: S310 — fixed http(s) addresses
    try:
        with urllib.request.urlopen(request, timeout=PROBE_SECONDS) as response:  # noqa: S310
            return int(response.status)
    except urllib.error.HTTPError as error:
        return int(error.code)
    except (OSError, ValueError):
        return 0


def checks(  # noqa: PLR0913 — the last two are seams a test needs
    environ: Mapping[str, str],
    *,
    offline: bool,
    ledger: Ledger,
    gateway: str,
    claude_voice_file: pathlib.Path = sessions.ENV_FILE,
    status: Callable[[str, Mapping[str, str]], int] = http_status,
) -> list[Check]:
    """Every check, in the order a newcomer should fix them."""
    return [
        _openai_key(environ, offline=offline, status=status),
        _budget(ledger),
        _hermes(environ, gateway, offline=offline, status=status),
        _claude_voice(environ, claude_voice_file, offline=offline, status=status),
    ]


def summary(found: list[Check]) -> dict[str, object]:
    """The report an assistant reads: ready once every required check passes."""
    return {"ready": all(c.ok for c in found if c.required), "checks": [asdict(c) for c in found]}


def _openai_key(environ: Mapping[str, str], *, offline: bool, status: Callable[..., int]) -> Check:
    key = environ.get("OPENAI_API_KEY", "")
    if not key:
        return Check(
            "openai_key",
            required=True,
            ok=False,
            detail="no OpenAI API key, so no voice session can be opened",
            fix=f"put OPENAI_API_KEY=<your key> in {SETTINGS}; keys are made at platform.openai.com/api-keys",
        )
    if offline:
        return Check(
            "openai_key", required=True, ok=True, detail="a key is set; not asked of OpenAI (--offline)"
        )
    code = status(OPENAI_MODELS, {"Authorization": f"Bearer {key}"})
    if code == HTTPStatus.OK:
        return Check("openai_key", required=True, ok=True, detail="OpenAI accepts the key")
    if code == 0:
        return Check(
            "openai_key",
            required=True,
            ok=False,
            detail="OpenAI could not be reached",
            fix="check the connection",
        )
    return Check(
        "openai_key",
        required=True,
        ok=False,
        detail=f"OpenAI refused the key ({code})",
        fix=f"make a new key at platform.openai.com/api-keys and put it in {SETTINGS}",
    )


def _budget(ledger: Ledger) -> Check:
    if ledger.remaining_usd() > 0:
        return Check("budget", required=True, ok=True, detail="this month's ceiling is not spent")
    return Check(
        "budget",
        required=True,
        ok=False,
        detail="this month's ceiling is spent, so no session is opened until next month",
        fix=f"raise VOICE_BRIDGE_CEILING_USD in {SETTINGS}, if you mean to spend more",
    )


def _hermes(environ: Mapping[str, str], gateway: str, *, offline: bool, status: Callable[..., int]) -> Check:
    if offline:
        return Check("hermes", required=False, ok=False, detail="the planner was not asked (--offline)")
    code = status(
        f"{gateway}/v1/capabilities", {"Authorization": f"Bearer {environ.get('HERMES_API_KEY', '')}"}
    )
    if code == HTTPStatus.OK:
        return Check("hermes", required=False, ok=True, detail=f"the planner answers at {gateway}")
    if code == 0:
        return Check(
            "hermes",
            required=False,
            ok=False,
            detail=f"no planner answers at {gateway}, so it cannot be chosen",
            fix="to talk to a planner, install Hermes Agent: github.com/NousResearch/hermes-agent",
        )
    return Check(
        "hermes",
        required=False,
        ok=False,
        detail=f"the planner at {gateway} refused the bridge ({code})",
        fix=f"put HERMES_API_KEY=<the gateway's key> in {SETTINGS}",
    )


def _claude_voice(
    environ: Mapping[str, str], file: pathlib.Path, *, offline: bool, status: Callable[..., int]
) -> Check:
    if offline:
        return Check(
            "claude_voice",
            required=False,
            ok=False,
            detail="claude-voice was not asked (--offline)",
        )
    address = environ.get("VOICE_BRIDGE_CLAUDE_VOICE") or sessions.ADDRESS
    root = address.removesuffix("/mcp")
    if status(f"{root}/healthz", {}) != HTTPStatus.OK:
        return Check(
            "claude_voice",
            required=False,
            ok=False,
            detail=f"claude-voice does not answer at {root}, so no Claude session can be chosen",
            fix="to talk to Claude sessions, install github.com/roykollensvendsen/claude-voice",
        )
    if not (environ.get("CLAUDE_VOICE_TOKEN") or _token_in(file)):
        return Check(
            "claude_voice",
            required=False,
            ok=False,
            detail="claude-voice answers, but the bridge has no token for it",
            fix=f"claude-voice keeps CLAUDE_VOICE_TOKEN in {file}; the bridge reads it from there",
        )
    return Check("claude_voice", required=False, ok=True, detail=f"claude-voice answers at {root}")


def _token_in(file: pathlib.Path) -> bool:
    environ: dict[str, str] = {}
    apply_settings(environ, file)
    return bool(environ.get("CLAUDE_VOICE_TOKEN"))


def environment() -> dict[str, str]:
    """The environment of this process, as the checks read it."""
    return dict(os.environ)
