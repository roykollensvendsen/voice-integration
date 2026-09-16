# The voice contract

What the realtime model is given, and why it is this small.

A realtime session is billed for its own instructions on every cached miss, and
a model choosing between six well-named tools is more reliable than one choosing
between thirty. So the surface is fixed at six, each one standing for exactly
one gateway call, and adding a seventh is a decision record rather than a
commit.

## The surface

<!-- normative: voice tools -->

| Tool | Arguments | What it does | Gateway call |
|---|---|---|---|
| `agent_task` | `agent`, `instruction`, `room` | gives one agent one task, answers with a run identifier | `POST /v1/runs` |
| `approval_resolve` | `run_id`, `choice` | answers one approval the gateway is blocked on | `POST /v1/runs/{run_id}/approval` |
| `run_status` | `run_id` | says what a run is doing now | `GET /v1/runs/{run_id}` |
| `run_steer` | `run_id`, `guidance` | says something to an agent that is already working | `POST /v1/runs/{run_id}/steer` |
| `run_stop` | `run_id` | interrupts a run that is going the wrong way | `POST /v1/runs/{run_id}/stop` |
| `session_recall` | — | says which sessions exist, so one can be picked up again | `GET /api/sessions` |

`voice_bridge.contract.VOICE_TOOLS` holds the same six, and `voicebridge check`
fails when this table and that tuple disagree.

## The shape a session is configured with

```console
$ voicebridge tools --names
agent_task
approval_resolve
run_status
run_steer
run_stop
session_recall
```

The full function definitions, in the form the Realtime API takes, come from
`voicebridge tools` without `--names`.

## What each call becomes

`dispatch --dry-run` answers the question a reviewer actually has, which is what
leaves the machine:

```console
$ voicebridge dispatch --dry-run agent_task '{"agent": "claude-code", "instruction": "run the tests", "room": "evening"}'
POST http://localhost:8642/v1/runs
{"input": "run the tests", "model": "claude-code", "session_id": "evening"}
```

`agent` becomes Hermes' `model`, because that is the field Hermes resolves a
route from, and a route is what selects the agent behind an alias. `room`
becomes `session_id`, which is the identifier the laptop view subscribes to.

## What the model is told

The session preamble is fixed, and it is short for the reason
[`specification.md`](specification.md) gives. It says four things and no more:

1. You are a voice interface to an agent system, not the agent.
2. Name the agent and the room; never describe the work in detail.
3. Read back run identifiers slowly, because they are how the person addresses
   what you started.
4. When a gateway reply is long, say the first sentence and stop.

It never contains: the list of repositories, the contents of any of them, the
names of every available agent, or the history of the session. Those are
lookups.

## Refusals

A call the voice layer may not make is refused at the bridge, before any
request is planned, and the refusal is what the person hears:

```console
$ voicebridge dispatch --dry-run approval_resolve '{"run_id": "run_ab12", "choice": "always"}'
refused: 'always' would outlive this call; voice may answer deny or once
```

Why that particular refusal is a rule rather than a preference is
[`permissions.md`](permissions.md).
