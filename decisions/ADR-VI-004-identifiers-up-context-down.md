# ADR-VI-004: Context flows down and identifiers flow up

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

The first sketch had the voice model as the brain: it would hold the
conversation, know what the agents were doing, and decide what to do next. That
is the expensive arrangement in every direction.

Realtime audio is billed per audio token. A minute of the person speaking is
about 600 tokens; a minute of the model speaking is about 1200. On the full
model that is $32 and $64 per million; on the mini, $10 and $20. Measured
sessions put a working agent at $0.06–0.11 a minute on the full model, $0.02–
0.05 on the mini, and $0.18–0.46 when prompt caching is not holding.

The token cost is only half of it. Reading a stack trace aloud is worse than
useless to a listener, and a preamble that grows with the number of agents is a
preamble that stops being cacheable.

## Options considered

**The voice model holds the conversation state.** Natural, and what every
example does. Rejected on both cost and audibility.

**Stream run events into the voice session so it can narrate.** Rejected: a
stream of `tool.started` events is the definition of something not worth saying
aloud, and it bills as input tokens the whole time.

**Summarise on the bridge, cap the reply, keep the detail addressable.**
Accepted.

## Decision

The voice plane holds the last few turns of speech and six tool definitions.
Everything else is looked up. Replies spoken to the person are capped at 320
characters by `voice_bridge.speech.SPOKEN_REPLY_MAX_CHARS`, and always carry the
identifier that fetches the detail elsewhere.

## Consequences

The session preamble is fixed bytes and caches; the bill is roughly a function
of how long someone talks rather than of how much the agents did.

What gets worse: the voice interface is less impressive. It cannot recite what
an agent found, and a person who wants detail has to go to a screen. There will
be moments where the cap cuts something the person wanted. The cap is one
constant in one file, and moving it is a decision with a number attached rather
than a judgement call in the moment.

## Related

[`docs/specification.md`](../docs/specification.md).
