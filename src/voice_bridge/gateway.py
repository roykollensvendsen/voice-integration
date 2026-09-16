"""The one place a voice tool call becomes an HTTP request to the Hermes gateway.

Every endpoint used here is named in `docs/hermes-contract.md`, and
`voicebridge check` compares the two. The client is the standard library on
purpose: this process sits between a paid audio stream and an agent swarm, and
the fewer things in it that can be supply-chain compromised, the better.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

from voice_bridge.contract import BY_NAME, DEFAULT_GATEWAY, Tool
from voice_bridge.policy import Capabilities, Refused
from voice_bridge.speech import say

#: How long a voice tool call may take before the speaker is told it is slow.
#: A run is started, not awaited: the gateway answers `/v1/runs` immediately.
TIMEOUT_SECONDS = 10.0

_ALLOWED_SCHEMES = ("http://", "https://")


@dataclass(frozen=True)
class Request:
    """The request one voice tool call becomes."""

    method: str
    url: str
    body: dict[str, Any] | None

    def rendered(self) -> str:
        """The request as a person reads it, for `dispatch --dry-run`."""
        first = f"{self.method} {self.url}"
        return first if self.body is None else f"{first}\n{json.dumps(self.body)}"


def plan(name: str, arguments: dict[str, Any], gateway: str = DEFAULT_GATEWAY) -> Request:
    """Work out the request a voice tool call makes, without making it."""
    tool = BY_NAME.get(name)
    if tool is None:
        message = f"no voice tool named {name!r}"
        raise Refused(message)
    _require_arguments(tool, arguments)
    path = tool.path
    for argument in tool.arguments:
        placeholder = "{" + argument.name + "}"
        if placeholder in path:
            # RULE: a path argument goes into the URL, never into the body
            path = path.replace(placeholder, str(arguments[argument.name]))
    body: dict[str, Any] | None = None
    if tool.method != "GET":
        body = {
            field: arguments[argument]
            for argument, field in tool.body_fields
            if arguments.get(argument) is not None
        }
    return Request(method=tool.method, url=gateway.rstrip("/") + path, body=body)


def call(
    name: str,
    arguments: dict[str, Any],
    gateway: str = DEFAULT_GATEWAY,
    capabilities: Capabilities | None = None,
    key: str | None = None,
) -> str:
    """Make one voice tool call and return the sentence to speak."""
    (capabilities or Capabilities()).permit(name, arguments)
    request = plan(name, arguments, gateway)
    return say(name, send(request, key))


def send(request: Request, key: str | None = None) -> Any:  # noqa: ANN401 — the gateway's own JSON
    """Send one planned request and return the decoded reply."""
    # RULE: only an HTTP gateway URL is ever opened
    if not request.url.startswith(_ALLOWED_SCHEMES):
        message = f"refusing a gateway URL that is not HTTP: {request.url}"
        raise Refused(message)
    data = None if request.body is None else json.dumps(request.body).encode()
    headers = {"Content-Type": "application/json"}
    token = key if key is not None else os.environ.get("HERMES_API_KEY", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    prepared = urllib.request.Request(request.url, data=data, headers=headers, method=request.method)  # noqa: S310 — the scheme is checked above
    try:
        with urllib.request.urlopen(prepared, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 — as above
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as failure:
        return json.loads(failure.read() or b'{"error": {"message": "no detail"}}')


#: How long a spoken request may take before the person is told to come back to
#: it. Long enough for the short questions people actually ask out loud, short
#: enough that nobody thinks the line went dead.
PATIENCE_SECONDS = 25.0

#: How often to look. A run finishes when it finishes; looking oftener than this
#: only costs requests.
POLL_SECONDS = 1.5

#: Every gateway path used outside the six voice tools. `voicebridge check`
#: compares this and their paths against `docs/hermes-contract.md`, so a path
#: reached from anywhere has to be written down somewhere a person reads.
BESIDES_THE_TOOLS: tuple[str, ...] = ("/v1/runs/{run_id}/events",)

#: A stream is meant to stay open. The gateway sends a keepalive every thirty
#: seconds, so anything longer than that without a byte is a dead connection.
STREAM_TIMEOUT_SECONDS = 90.0


def wait_for(
    run_id: str,
    gateway: str = DEFAULT_GATEWAY,
    patience: float = PATIENCE_SECONDS,
    key: str | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:  # noqa: ANN401 — the gateway's own JSON
    """Poll a run until it stops running, or until patience runs out."""
    request = plan("run_status", {"run_id": run_id}, gateway)
    deadline = time.monotonic() + patience
    seen: Any = {}
    while True:
        seen = send(request, key)
        status = seen.get("status") if isinstance(seen, dict) else None
        if status not in ("queued", "running", None) or time.monotonic() >= deadline:
            return seen
        sleep(POLL_SECONDS)


def events(run_id: str, gateway: str = DEFAULT_GATEWAY, key: str | None = None) -> Iterator[dict[str, Any]]:
    """Every lifecycle event of a run, as the gateway sends them.

    This is the stream `docs/hermes-contract.md` says the voice plane must not
    consume: a run of `tool.started` events is the definition of something not
    worth saying aloud. It is for the screen.
    """
    url = gateway.rstrip("/") + f"/v1/runs/{run_id}/events"
    if not url.startswith(_ALLOWED_SCHEMES):
        message = f"refusing a gateway URL that is not HTTP: {url}"
        raise Refused(message)
    token = key if key is not None else os.environ.get("HERMES_API_KEY", "")
    headers = {"Accept": "text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310 — scheme checked above
    with urllib.request.urlopen(request, timeout=STREAM_TIMEOUT_SECONDS) as stream:  # noqa: S310 — as above
        for raw in stream:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("data:"):
                try:
                    yield json.loads(line[5:])
                except json.JSONDecodeError:
                    continue


def tool_schemas() -> list[dict[str, object]]:
    """Every voice tool, in the shape a realtime session is configured with."""
    return [tool.schema() for tool in BY_NAME.values()]


def _require_arguments(tool: Tool, arguments: dict[str, Any]) -> None:
    missing = [a.name for a in tool.arguments if a.required and not arguments.get(a.name)]
    # RULE: a required argument missing is refused before a request is planned
    if missing:
        message = f"{tool.name} needs {', '.join(missing)}"
        raise Refused(message)
    for argument in tool.arguments:
        given = arguments.get(argument.name)
        if argument.choices and given is not None and str(given) not in argument.choices:
            message = f"{argument.name} must be one of {', '.join(argument.choices)}"
            raise Refused(message)
