# ADR-VI-017: The voice model is gpt-live-1

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16. Supersedes
[ADR-VI-007](ADR-VI-007-mini-is-the-default-voice-model.md).

## Context

[ADR-VI-007](ADR-VI-007-mini-is-the-default-voice-model.md) chose
`gpt-realtime-mini` as the default and promised a monthly ceiling it could not
put a number on. It was written from a list of realtime models, filtered for
`realtime` and `audio` in the identifier.

That filter missed two models. `gpt-live-1` exists, and it is what the person
meant all along when they said "GPT Live" — the name in the ChatGPT app is the
name of the model. It was released days before that record was written.

Three things about it, checked by calling the API and recorded in
[`evidence/api/gpt-live-1-transport-and-delegation.md`](../evidence/api/gpt-live-1-transport-and-delegation.md):

* **It is priced flat.** "Voice sessions cost $0.05 per minute, billed per
  second." No audio-token arithmetic, and no cliff when prompt caching stops
  holding — which on the realtime models turns $0.02–0.05 a minute into
  $0.18–0.46.
* **It is built for this architecture.** The model page says it can "delegate
  reasoning and tool use to a backend agent", and the guide names *client
  delegation*: your application connects "any model, agent harness, or service"
  and "owns permissions, confirmations, private function execution, and durable
  task state". That is this specification with different nouns.
* **It cannot be reached over a WebSocket.** That is
  [ADR-VI-018](ADR-VI-018-the-client-is-a-browser-page.md)'s problem, and the
  reason these are two records rather than one.

## Options considered

**Stay on `gpt-realtime-2.1-mini`.** It works over a WebSocket, which was
connected to successfully while writing this, and it is the cheapest thing on
the list at its best. Rejected: it is not what was asked for, its price is a
range rather than a number, and its worst case is nine times its best.

**Use the full `gpt-realtime-2.1`.** Three times mini's price for the same
family and the same billing model. Rejected for the same reasons.

**Use `gpt-live-1`.** Accepted.

## Decision

`gpt-live-1` is the voice model. There is no mini variant and no per-session
choice of a cheaper one, because there is nothing to choose between.

## Consequences

The ceiling ADR-VI-007 promised and could not state is now arithmetic: $0.05 a
minute means one hour of open microphone costs $3.00, and a monthly ceiling is a
number of minutes. That is the first time in this design that a budget can be
set before the bill arrives rather than after.

What gets worse. The floor rises: the cheapest realtime session was $0.02 a
minute and this is $0.05 whatever happens, so short, frequent conversations cost
more than they would have. There is no cheaper model to fall back to, so the
only lever left is how long the microphone is open — which makes
[ADR-VI-010](ADR-VI-010-one-live-microphone.md)'s explicit claim carry weight it
was not chosen for. And the transport is not negotiable, which costs a whole
decision on its own.

The number is still not written down. It goes into the first configuration file,
and until then this record is as unfinished as the one it replaces.

## Related

[`docs/specification.md`](../docs/specification.md),
[`evidence/api/gpt-live-1-transport-and-delegation.md`](../evidence/api/gpt-live-1-transport-and-delegation.md).
