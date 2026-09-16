# voice-integration

Talk to your coding agents. From the phone, from the laptop, in the same
session, without handing a microphone the keys to your repositories.

A thin voice layer in front of the [Hermes Agent](https://github.com/NousResearch/hermes-agent)
gateway, which already knows how to run Claude Code, OpenCode, DeepSeek Harness
and its own subagents, hold their sessions, stream their events and stop them to
ask you a question. This repository builds the edge: the six tools a realtime
voice model is given, the translation of a gateway reply into a sentence worth
hearing, and the permission layer that can only ever narrow.

```
  phone                laptop
    │ microphone         │ microphone        │ screen
    ▼                    ▼                   │
      OpenAI Realtime API                    │     the voice plane
                │ tool calls (JSON)          │
                ▼                            │
            voice-bridge  ◄──────────────────┘            the edge
                │ HTTPS + Bearer
                ▼
      Hermes gateway  /v1/runs  /api/sessions         the control plane
                │ A2A, MCP, subagents, toolsets
                ▼
  Claude Code   OpenCode   DeepSeek Harness             the work plane
```

Both ends carry a microphone; only the laptop carries a screen, and that is its
only privilege.

**Context flows down, identifiers flow up.** The voice plane learns that
`run_ab12` is waiting on an approval. It never learns the diff.

## Where it is

Step one of four is done: a voice tool call travels through the permission
layer, becomes a real request to a real gateway, and comes back as a sentence.
The microphone is step two, and it waits on
[an answer about who pays for the audio](docs/open-questions.md).

## The surface

Six tools, fixed, because a realtime session is billed for its own instructions
and a model picking between six well-named things is more reliable than one
picking between thirty:

```console
$ voicebridge tools --names
agent_task
approval_resolve
run_status
run_steer
run_stop
session_recall
```

What a call becomes, before any of it leaves the machine:

```console
$ voicebridge dispatch --dry-run agent_task '{"agent": "claude-code", "instruction": "run the tests", "room": "evening"}'
POST http://localhost:8642/v1/runs
{"input": "run the tests", "model": "claude-code", "session_id": "evening"}
```

And what the voice layer will not do, however nicely you ask it:

```console
$ voicebridge dispatch --dry-run approval_resolve '{"run_id": "run_ab12", "choice": "always"}'
refused: 'always' would outlive this call; voice may answer deny or once
```

Standing permissions are not granted by a channel that is used while walking and
mishears short words. [Why that is a rule](decisions/ADR-VI-003-the-voice-layer-can-only-narrow.md),
not a preference.

## Reading it

| Start here | For |
|---|---|
| [`docs/specification.md`](docs/specification.md) | the system, and the rules the cost of audio forces on it |
| [`docs/open-questions.md`](docs/open-questions.md) | the eleven things that are not settled, and what would settle each |
| [`docs/voice-contract.md`](docs/voice-contract.md) | the six tools, and what the model is told |
| [`docs/hermes-contract.md`](docs/hermes-contract.md) | what we call on the gateway, and what we deliberately do not |
| [`docs/permissions.md`](docs/permissions.md) | three layers, and the invariant that makes them worth having |
| [`decisions/`](decisions/README.md) | why it is this and not something else |

## Running the checks

Every fact stated twice here is compared by something that can fail:

```console
$ voicebridge check .
voice tools: 6 in docs/voice-contract.md, 6 in the code, agreed
gateway paths: 6 in docs/hermes-contract.md, 6 in the code, agreed
rules: 3 in the source, 3 in scripts/mutations.toml, agreed
```

The rest of the gates, and how a change is made, are in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

Apache-2.0.
