# The gateway contract

What this bridge consumes from Hermes, and what it deliberately does not.

Everything here is Hermes' `api_server` platform adapter, the one that serves an
OpenAI-compatible surface plus a proprietary run API. It listens on port 8642 by
default and requires `API_SERVER_KEY`; the bridge sends it as a bearer token.

## What we call

<!-- normative: gateway paths -->

| Method | Path | Why we call it | Answered with |
|---|---|---|---|
| `POST` | `/v1/runs` | start one agent run and return at once | `run_id`, `202` |
| `GET` | `/v1/runs/{run_id}` | poll a run for the one sentence we speak | a `hermes.run` status object |
| `POST` | `/v1/runs/{run_id}/approval` | answer an approval the run is blocked on | the resolved choice |
| `POST` | `/v1/runs/{run_id}/steer` | inject guidance into a running agent | accepted, or `409` |
| `POST` | `/v1/runs/{run_id}/stop` | interrupt a run | the new status |
| `GET` | `/api/sessions` | list the rooms that can be picked up again | `{object, data, limit, offset, has_more}` |
| `GET` | `/v1/runs/{run_id}/events` | follow a run for the screen, never for the voice | server-sent `tool.started`, `tool.completed`, `message.delta`, `run.completed` |

`voicebridge check` fails when this table and the paths in
`voice_bridge.contract.VOICE_TOOLS` disagree.

## The shapes it answers with

Read off a running Hermes 0.21.3 rather than assumed, because two of the shapes
this page used to state were wrong and no test could see it.

* A **session** is keyed `id`, not `session_id`. It also carries `title`,
  `model`, `message_count`, `started_at` and `ended_at`. Every other endpoint
  takes the same value as `session_id`, which is how the wrong name survived.
* A **run that failed** answers `200`, not an error status. Its status object
  has `status: "failed"` and the reason in `error`, alongside
  `object: "hermes.run"`. A refusal is different: an envelope holding `error`
  and nothing else. `object` is what separates them, and mistaking one for the
  other told the person the gateway had refused when the gateway was fine.
* **Run state lives in memory.** Restarting the gateway loses every run, and a
  poll for one afterwards answers `404 run_not_found`. Sessions survive; runs do
  not.

## The fields we send

* `POST /v1/runs` takes `input` (the instruction), `model` (the route, which is
  how an agent alias is selected) and `session_id` (the room). It also takes
  `instructions`, and the bridge sends one: a voice turn must end with something
  to say, and the gateway's default is to dispatch long work to a background
  subagent, complete the run at once, and deliver the answer later as a message
  in the session. Heard from the person's side that is the system saying it has
  started and then never coming back. `server.TURN_INSTRUCTIONS` is what asks it
  to finish inside the turn.
* `previous_response_id` and `conversation_history` are not sent, because
  carrying conversation history through the voice plane is precisely what this
  design refuses to do.
* `POST /v1/runs/{run_id}/approval` takes `choice`, one of `once`, `session`,
  `always` or `deny`. The bridge will only ever send two of them, for the reason
  in [`permissions.md`](permissions.md).
* `POST /v1/runs/{run_id}/steer` takes `input`. It answers `409` when the run is
  not in a state that accepts steering, which is a thing the person should hear
  rather than a thing to retry.

## What we do not call, on purpose

The event stream used to be on this list. It is now read, on its own thread,
and relayed to the page's screen panel — never to the voice plane, which is
what that line was really protecting. A stream of tool-started events remains
the definition of something not worth saying aloud.

* `/v1/chat/completions` and `/v1/responses` would make the bridge a chat client
  and put the gateway's thinking back into the audio path.
* `/api/sessions/{id}/messages` returns history, which the voice plane has no
  business holding.

## Headers

| Header | Carries | Set by |
|---|---|---|
| `Authorization: Bearer …` | `API_SERVER_KEY` | the bridge, from `HERMES_API_KEY` |
| `X-Hermes-Session-Id` | session continuity for the stateless endpoints | not yet; the run API takes `session_id` in the body |
| `X-Hermes-Session-Key` | long-term memory scope | not yet, and see the open questions |

## What Hermes tells us about itself

`GET /v1/capabilities` is machine-readable, and worth calling before assuming
any of the above. Today it reports `run_submission`, `run_status`,
`run_events_sse`, `run_stop`, `run_steer`, `run_approval_response`,
`approval_events` and `session_resources` as available — and `realtime_voice`
and `audio_api` as not. The second pair is the reason this repository exists;
the day either flips to true is the trigger on a row in
[`decisions/deferred.md`](../decisions/deferred.md).
