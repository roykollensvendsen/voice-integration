# The voice contract

What the bridge will do, and why it is this small.

The voice model is given no functions at all. `gpt-live-1` in client delegation
mode says only that it wants help, with an opaque identifier and no task text;
the bridge keeps the transcript, works out what was asked, does it, and appends
a string for the model to say aloud.
[ADR-VI-019](../decisions/ADR-VI-019-a-delegation-not-a-tool-list.md) records
why that is the mode.

So these six are not a menu handed to a model. They are the only six things the
bridge will do when a delegation arrives, which makes them the boundary
[`permissions.md`](permissions.md) describes rather than a suggestion to
something else. Adding a seventh is a decision record rather than a commit.

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

## The voice model calls nothing

It is worth saying plainly, because it comes up every time somebody looks at
this design: `gpt-live-1` never calls a tool. The vendor's own summary is that
it "listens, speaks, and decides when to ask the backend for help", while "the
backend reasons, uses tools, and returns results for GPT-Live to communicate".

That holds in both delegation modes. Client delegation gives it no functions at
all. Responses delegation registers functions, but a model of OpenAI's picks
them and the application still runs them — the voice model is outside either
way.

The tools people have seen it list in the ChatGPT app — web, files, images —
belong to that app's own backend, which stands exactly where the bridge and the
gateway stand here. Asking for the voice model to call tools directly is asking
for the Realtime API, which
[ADR-VI-017](../decisions/ADR-VI-017-the-voice-model-is-gpt-live-1.md) turned
down.

## How a turn works

1. The page streams audio. `session.input_transcript.delta` arrives on the data
   channel as the person speaks; the bridge keeps it.
2. The model decides it needs the backend and emits
   `session.delegation.created` with `delegation.id`. It carries no task text.
3. The bridge asks Hermes what to do with the transcript so far, which is
   `POST /v1/runs` — the gateway plans, as
   [ADR-VI-001](../decisions/ADR-VI-001-hermes-is-the-control-plane.md) says.
4. The bridge appends the answer with `session.commentary.append`, quoting the
   same `delegation_id`, and the model paraphrases it aloud.

Step 3 waits. A run is started and answered immediately with an identifier, and
an identifier is not an answer — nobody asks a question out loud in order to be
given a reference number. So the bridge polls the run and speaks its output.

Work that outlasts `gateway.PATIENCE_SECONDS` does not end the turn. The voice
says it is still going and will say when it is done, and the page keeps asking
the bridge until it is, then appends the answer as a second commentary on the
same delegation. Nobody has to remember a run identifier or ask again; that is
what repeated appends are for. The identifier stays on the screen, where it is
addressable without being spoken.

Waiting is not silence. The page appends a holding line the moment a delegation
arrives, because a slow answer with nothing said is indistinguishable from a
dropped call. A repeated append continues the same delegation, which is what
makes that allowed.

`session.thinking.append` carries something the model should know and not say.
Both take a plain string and both require the delegation identifier, including
when it is null.

An acknowledgment is not a receipt. The guide is explicit that it "is not proof
that the model has consumed or spoken the result, or that an external action
succeeded", so a person can hear nothing about something that has already run.
That is why approvals live in Hermes and not here.

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

The full definitions come from `voicebridge tools` without `--names`. They are
not sent to OpenAI: they are what the bridge dispatches against, and what a
reviewer reads to see the whole boundary in one place.

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
[`specification.md`](specification.md) gives. It is carried in the session the
bridge creates, never in the page, because the page is code a browser was
handed and the preamble is policy. It says four things and no more:

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
