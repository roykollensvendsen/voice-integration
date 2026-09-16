# What the Live API actually does, checked by calling it

*Run 2026-09-16 against `api.openai.com` with a project key. Every command below
can be repeated; each needs `OPENAI_API_KEY` in the environment. Nothing here is
quoted from a blog post, and where the documentation is the source it is named.*

This page exists because two claims that shaped
[ADR-VI-017](../../decisions/ADR-VI-017-the-voice-model-is-gpt-live-1.md) and
[ADR-VI-018](../../decisions/ADR-VI-018-the-client-is-a-browser-page.md) are the
kind that a page can state and an API can contradict.

## The model exists, and it is not in the realtime family

```
curl -s https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  | python3 -c "import json,sys; print([m['id'] for m in json.load(sys.stdin)['data'] if 'live' in m['id']])"
```

Answers `['gpt-live-transcribe', 'gpt-live-1']`. A search for `realtime` answers
ten other identifiers, and the two sets do not overlap. A filter for `realtime`
or `audio` — the obvious one — misses both, which is how this was nearly missed.

## It cannot be reached over a WebSocket

Connecting to `wss://api.openai.com/v1/realtime?model=gpt-live-1` is refused:

```
Model "gpt-live-1" is not supported in realtime mode.
```

and the socket closes with `4000 invalid_request_error.invalid_model`. The same
connection with `gpt-realtime-2.1-mini` succeeds and reports
`turn_detection.type = server_vad`, so the failure is the model and not the
call.

## The trap: minting a secret succeeds anyway

```
curl -s -X POST https://api.openai.com/v1/realtime/client_secrets \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"session":{"type":"realtime","model":"gpt-live-1"}}'
```

Answers `200` with a session object whose `model` is `gpt-live-1`. That secret
cannot be used: the connection it is for is refused. A design that checked the
mint and trusted it would have found this in the client instead.

## WebRTC is not a setting, it is the type

`POST /v1/live/sessions` with `{"session":{"transport":"websocket"}}` answers
`Only the webrtc transport is supported.`, and passing `transport` as a string
answers:

```
json: cannot unmarshal string into Go struct field
LiveSessionPostParam.transport of type common.LiveWebRTCTransport
```

The field is typed to one transport. Sending `{"transport":{"type":"webrtc"}}`
answers `An SDP offer is required.`, so a session is established by a WebRTC
handshake rather than minted and then connected to.

## Delegation, from the documentation

The [Live guide](https://developers.openai.com/api/docs/guides/live) names two
modes. Under *client delegation* it says you may "connect any model, agent
harness, or service your application runs", and that "your application owns
permissions, confirmations, private function execution, and durable task
state".

That sentence is this system's architecture with different nouns: the agent
harness is Hermes, the permissions are
[`docs/permissions.md`](../../docs/permissions.md), the confirmations are the
approval flow, and the durable task state is a room and its runs.

## Pricing, from the documentation

The [model page](https://developers.openai.com/api/docs/models/gpt-live-1)
states: "Voice sessions cost $0.05 per minute, billed per second", and that
backend model and tool usage are charged separately. Its knowledge cutoff is
2025-07-31, and it takes audio and text in and out.

## What this page does not establish

Whether the full-duplex behaviour is better than `gpt-realtime-2.1`. Third-party
write-ups claim a large gain on a benchmark; none of that was measured here, and
none of it should be repeated in this repository as though it were.
