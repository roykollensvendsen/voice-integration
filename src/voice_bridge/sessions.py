"""News from the Claude Code sessions claude-voice runs, and the answers they wait for.

Most coding work on this machine does not start from the voice. It starts in a
terminal, or from the phone through claude-voice, and when it finishes or stops
to ask for permission, somebody walking with the microphone open hears nothing.
claude-voice already keeps that news, one sentence per event, written to be read
aloud. This asks for it every few seconds and answers what is waiting. Nothing
here is a model call. ADR-VI-024.

The client is the slice of MCP over Streamable HTTP that three tools need, in
the standard library, like everything else in this process:
`docs/claude-voice-contract.md`.
"""

from __future__ import annotations

import itertools
import json
import os
import pathlib
import re
import urllib.error
import urllib.request
from typing import Any

from voice_bridge.policy import Refused

#: The three tools the bridge may call. Everything else claude-voice offers is a
#: request that needs planning, and planning is the gateway's.
TOOLS = ("whats_new", "approve", "deny")

#: What is worth saying aloud. The rest is shown and not said: a session that
#: started working is not news to somebody walking down the street.
SPOKEN = ("finished", "error", "needs_input", "needs_approval")

#: How often to ask. A poll is a local call that costs nothing, and six seconds
#: is quicker than anybody notices a silence.
POLL_SECONDS = 6.0
CALL_SECONDS = 10.0

ADDRESS = "http://127.0.0.1:8811/mcp"
ENV_FILE = pathlib.Path.home() / ".config" / "claude-voice" / "env"
PROTOCOL = "2025-06-18"

#: "Approval 3: yes or no?" — a number nobody needs to hear.
_ASKING = re.compile(r"\s*Approval\s+\S+:\s*yes or no\?", re.IGNORECASE)
_EXPIRED = re.compile(r"\bApproval\s+\S+\s+for\b", re.IGNORECASE)


def address() -> str:
    """Where claude-voice listens."""
    return os.environ.get("VOICE_BRIDGE_CLAUDE_VOICE", ADDRESS)


def token(env_file: pathlib.Path = ENV_FILE) -> str | None:
    """claude-voice's local token, or None when there is none to be had."""
    if os.environ.get("CLAUDE_VOICE_TOKEN"):
        return os.environ["CLAUDE_VOICE_TOKEN"]
    try:
        lines = env_file.read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        name, _, value = line.partition("=")
        if name.strip() == "CLAUDE_VOICE_TOKEN" and value.strip():
            return value.strip().strip("\"'")
    return None


def spoken(text: str) -> str:
    """The sentence claude-voice wrote, without the number in it."""
    # RULE: an approval number is never read aloud
    text = _ASKING.sub(" Yes or no?", text)
    return _EXPIRED.sub("The request from", text).strip()


class Client:
    """One MCP session with claude-voice, opened on first use and again when it expires."""

    def __init__(self, url: str, secret: str) -> None:
        """Talk to claude-voice at `url`, with its local token."""
        self.url = url
        self.secret = secret
        self.session: str | None = None
        self.ids = itertools.count(1)

    def call(self, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run one tool and return its structured result."""
        # RULE: the bridge calls claude-voice only to hear news and answer one request
        if tool not in TOOLS:
            refusal = f"{tool} is not the bridge's to call"
            raise Refused(refusal)
        message = {"method": "tools/call", "params": {"name": tool, "arguments": arguments or {}}}
        for attempt in range(2):
            if self.session is None:
                self._open()
            try:
                reply = self._post(message)
                break
            except urllib.error.HTTPError as failure:
                # An expired session is a 404, and the cure is a new one.
                if failure.code != 404 or attempt:  # noqa: PLR2004 — HTTP's own number
                    raise
                self.session = None
        result = (reply or {}).get("result") or {}
        if result.get("isError"):
            said = " ".join(str(part.get("text", "")) for part in result.get("content") or [])
            raise Refused(said or f"{tool} was refused")
        return result.get("structuredContent") or {}

    def _open(self) -> None:
        self._post(
            {
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL,
                    "capabilities": {},
                    "clientInfo": {"name": "voice-bridge", "version": "0"},
                },
            }
        )
        self._post({"method": "notifications/initialized"}, notification=True)

    def _post(self, message: dict[str, Any], *, notification: bool = False) -> dict[str, Any] | None:
        sent = {"jsonrpc": "2.0", **message}
        if not notification:
            sent["id"] = next(self.ids)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.secret}",
        }
        if self.session:
            headers["Mcp-Session-Id"] = self.session
            headers["MCP-Protocol-Version"] = PROTOCOL
        request = urllib.request.Request(  # noqa: S310 — a local address from configuration
            self.url, data=json.dumps(sent).encode(), headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=CALL_SECONDS) as answer:  # noqa: S310 — as above
            self.session = answer.headers.get("Mcp-Session-Id") or self.session
            body = answer.read().decode()
            streamed = "text/event-stream" in answer.headers.get("Content-Type", "")
        if notification or not body.strip():
            return None
        # A stream may carry notifications before the reply; the reply is the
        # one with our id.
        replies = [body]
        if streamed:
            replies = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
        for reply in replies:
            found = json.loads(reply or "{}")
            if isinstance(found, dict) and found.get("id") == sent["id"]:
                return found
        return None


def news(client: Client, cursor: str | None) -> tuple[str, list[dict[str, Any]]]:
    """What happened since `cursor`, and the cursor to ask from next time."""
    got = client.call("whats_new", {"cursor": cursor} if cursor else {})
    # RULE: old news is never read out
    happened = (got.get("events") or []) if cursor else []
    return str(got.get("cursor") or cursor or ""), [
        {**event, "text": spoken(str(event.get("text", "")))} for event in happened if isinstance(event, dict)
    ]
