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
| `GET` | `/api/sessions` | list the rooms that can be picked up again | a list of sessions |

`voicebridge check` fails when this table and the paths in
`voice_bridge.contract.VOICE_TOOLS` disagree.

## The fields we send

* `POST /v1/runs` takes `input` (the instruction), `model` (the route, which is
  how an agent alias is selected) and `session_id` (the room). It also accepts
  `instructions`, `previous_response_id` and `conversation_history`; the bridge
  sends none of them, because carrying conversation history through the voice
  plane is precisely what this design refuses to do.
* `POST /v1/runs/{run_id}/approval` takes `choice`, one of `once`, `session`,
  `always` or `deny`. The bridge will only ever send two of them, for the reason
  in [`permissions.md`](permissions.md).
* `POST /v1/runs/{run_id}/steer` takes `input`. It answers `409` when the run is
  not in a state that accepts steering, which is a thing the person should hear
  rather than a thing to retry.

## What we do not call, on purpose

* `GET /v1/runs/{run_id}/events` is the server-sent event stream of the run's
  lifecycle. It belongs to the laptop view, not to the voice plane: a stream of
  tool-started events is the definition of something not worth saying aloud.
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
