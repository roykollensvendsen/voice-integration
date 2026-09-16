# ADR-VI-018: The client is a browser page, served by the bridge

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16. Supersedes
[ADR-VI-008](ADR-VI-008-a-native-client-on-each-device.md) and
[ADR-VI-006](ADR-VI-006-no-runtime-dependencies.md).

## Context

[ADR-VI-008](ADR-VI-008-a-native-client-on-each-device.md) chose a native client
on each device, weighing a browser's free echo cancellation against a phone
browser losing the microphone when the screen locks. The yardstick the person
set was explicit: as close as possible to the experience of GPT Live.

Then [ADR-VI-017](ADR-VI-017-the-voice-model-is-gpt-live-1.md) established that
GPT Live is a model, and that it is reachable one way only. `POST
/v1/live/sessions` types its `transport` field as WebRTC; a string is refused by
the unmarshaller, and a WebSocket connection to the model is closed with
`invalid_model`. Sending the right shape answers `An SDP offer is required`, so
a session is a WebRTC handshake rather than a token the client connects with.

So the yardstick and the transport point the same way, and away from where
ADR-VI-008 landed. WebRTC and acoustic echo cancellation are the two hard parts
of a voice client, and a browser has both already.

## Options considered

**A native client with `aiortc`.** Keeps ADR-VI-008 whole, and buys a global
hotkey and a process that survives the browser closing. Rejected: it means
writing WebRTC session setup in Python on top of configuring PipeWire's echo
canceller, and both have to work before a single word is heard. It is the
largest of the three by a wide margin, and none of the work is about this
system.

**Stay on `gpt-realtime-2.1-mini` so a WebSocket still works.** Keeps the native
client cheap. Rejected in ADR-VI-017: it is not the thing that was asked for.

**A browser page served by the bridge.** Accepted.

## Decision

The client is a web page the bridge serves. WebRTC, echo cancellation, noise
suppression and microphone permission all come from the browser. The bridge
creates the session against `/v1/live/sessions`, exchanging the page's offer for
an answer, so the API key never reaches the page.

## Consequences

The client shrinks to a page and the two hard parts stop being ours. On the
laptop it loses nothing that matters: the screen is not locked and the person is
sitting in front of it.

This supersedes [ADR-VI-006](ADR-VI-006-no-runtime-dependencies.md). The bridge
now serves files and terminates an HTTP request from a browser, so it needs a
web framework, and the process holding the gateway key stops being a page of
standard library. That was the whole argument of that record, and it is being
given up deliberately rather than quietly: the alternative was the same
complexity in a native client, plus a second audio stack.

What gets worse on the phone is real and unresolved. A browser tab loses the
microphone when the screen locks, which was the case that justified an Android
client at all. That client is still deferred, and when it is written it will
need WebRTC natively — so the problem ADR-VI-008 was solving has been postponed,
not answered.

The laptop also has no hotkey now. Claiming the microphone
([ADR-VI-010](ADR-VI-010-one-live-microphone.md)) happens in the page, which
means it happens only when the page is in front of you.

## Related

[`docs/specification.md`](../docs/specification.md),
[ADR-VI-017](ADR-VI-017-the-voice-model-is-gpt-live-1.md).
