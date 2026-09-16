# ADR-VI-007: The mini model is the default, and the bill has a ceiling

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

[ADR-VI-002](ADR-VI-002-our-own-realtime-client.md) settled that the voice layer
is a client we own against the Realtime API. That makes the audio a metered bill
where there had been none, on an account that until now was a free ChatGPT
subscription.

The rates, checked 2026-09-16: `gpt-realtime-2.1` is $32 per million audio
tokens in and $64 out; the mini variant is $10 and $20. A minute of the person
speaking is about 600 tokens, a minute of the model speaking about 1200.
Measured sessions put a working agent at $0.06–0.11 a minute on the full model,
$0.02–0.05 on the mini, and $0.18–0.46 when prompt caching is not holding.

The part that catches people is that a session bills while it is *connected*,
not while it is useful. An open microphone in a quiet room is a cost.

## Options considered

**The full model throughout.** Three times the price for a layer whose whole job
is routing and short sentences. Defensible if the mini turns out to mishear
Norwegian or to pick the wrong tool — but that is a thing to measure rather than
to assume, and measuring it costs a session.

**No budget at all.** Then [ADR-VI-002](ADR-VI-002-our-own-realtime-client.md)
falls and the fallback is Hermes' own push-to-talk: record, transcribe, answer,
speak. Not full duplex, not what was asked for, and free.

**Mini by default, full as a per-session choice.** Accepted.

## Decision

`gpt-realtime-mini` is the default. The full model is selected per session,
deliberately, and never as a fallback the system reaches for on its own. A
monthly ceiling lives in the configuration.

## Consequences

The bill becomes roughly a function of how long the microphone is open rather
than of how much the agents did, and the cheap default makes leaving it open
less alarming.

What gets worse: the ceiling has no number yet, and a ceiling with no number is
a wish. It gets one when the configuration is first written, and until then this
record is only half kept. The second gap is bigger and is not fixed by any
number here: the agents' own cost runs on Claude Code's subscription quota and
on the DeepSeek and OpenCode bills, and this ceiling does not see a penny of it.

## Related

[`docs/specification.md`](../docs/specification.md),
[ADR-VI-004](ADR-VI-004-identifiers-up-context-down.md).
