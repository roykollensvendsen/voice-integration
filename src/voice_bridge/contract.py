"""The tool surface the realtime voice model is given, and nothing else.

Six tools, fixed, so the session preamble is small enough to cache and stable
enough to stay cached. Each one names the single gateway call it makes, so the
surface a caller sees and the surface the gateway sees cannot drift apart
without `voicebridge check` noticing.

`docs/voice-contract.md` states the same six in a table a person reads. The
table and this module are compared by `voice_bridge.check`.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Gateway defaults, matching Hermes' own `platforms.api_server` defaults.
DEFAULT_GATEWAY = "http://localhost:8642"


@dataclass(frozen=True)
class Argument:
    """One argument of a voice tool, as the realtime model sees it."""

    name: str
    purpose: str
    required: bool = True
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tool:
    """One voice tool, and the single gateway call it stands for."""

    name: str
    purpose: str
    arguments: tuple[Argument, ...]
    method: str
    path: str
    body_fields: tuple[tuple[str, str], ...] = ()

    def schema(self) -> dict[str, object]:
        """The function definition handed to the realtime session."""
        properties: dict[str, object] = {}
        for argument in self.arguments:
            field: dict[str, object] = {"type": "string", "description": argument.purpose}
            if argument.choices:
                field["enum"] = list(argument.choices)
            properties[argument.name] = field
        return {
            "type": "function",
            "name": self.name,
            "description": self.purpose,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": [a.name for a in self.arguments if a.required],
                "additionalProperties": False,
            },
        }


VOICE_TOOLS: tuple[Tool, ...] = (
    Tool(
        name="agent_task",
        purpose="Give one coding agent one task and return its run identifier.",
        arguments=(
            Argument("agent", "which agent, by the alias the gateway routes"),
            Argument("instruction", "what to do, in the speaker's own words"),
            Argument("room", "the session the work belongs to", required=False),
        ),
        method="POST",
        path="/v1/runs",
        body_fields=(("instruction", "input"), ("agent", "model"), ("room", "session_id")),
    ),
    Tool(
        name="approval_resolve",
        purpose="Answer one approval the gateway is waiting on.",
        arguments=(
            Argument("run_id", "the run holding the approval"),
            Argument("choice", "allow this one call or refuse it", choices=("once", "deny")),
        ),
        method="POST",
        path="/v1/runs/{run_id}/approval",
        body_fields=(("choice", "choice"),),
    ),
    Tool(
        name="run_status",
        purpose="Say what one run is doing now.",
        arguments=(Argument("run_id", "the run to report on"),),
        method="GET",
        path="/v1/runs/{run_id}",
    ),
    Tool(
        name="run_steer",
        purpose="Say something to an agent that is already working.",
        arguments=(
            Argument("run_id", "the run to steer"),
            Argument("guidance", "what to tell it, in the speaker's own words"),
        ),
        method="POST",
        path="/v1/runs/{run_id}/steer",
        body_fields=(("guidance", "input"),),
    ),
    Tool(
        name="run_stop",
        purpose="Interrupt a run that is going the wrong way.",
        arguments=(Argument("run_id", "the run to interrupt"),),
        method="POST",
        path="/v1/runs/{run_id}/stop",
    ),
    Tool(
        name="session_recall",
        purpose="Say which sessions exist, so the speaker can pick one up again.",
        arguments=(),
        method="GET",
        path="/api/sessions",
    ),
)

BY_NAME: dict[str, Tool] = {tool.name: tool for tool in VOICE_TOOLS}
