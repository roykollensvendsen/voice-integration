# ADR-VI-014: The Linux client is built first, and it is evidence before it is a feature

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

[ADR-VI-002](ADR-VI-002-our-own-realtime-client.md) rests on a premise that has
not been tested: that what the person values about GPT Live is the interaction
and not the ChatGPT application around it. If it is the application, half of
this repository is wrong, and it is cheaper to find that out before the rest is
built than after.

[ADR-VI-008](ADR-VI-008-a-native-client-on-each-device.md) made that test more
expensive by choosing two native clients. It is still worth doing, and the
question is which client carries it.

## Options considered

**The Android application first.** It is the case that motivated the phone —
talking while walking. Rejected as the first one:
[ADR-VI-009](ADR-VI-009-everything-runs-on-the-laptop.md) means the gateway is a
laptop standing at home, so the walking case is the narrower one, not the wider
one. Echo cancellation there is also per-device and not guaranteed present,
which is a bad thing to meet while the premise is still unproven.

**Both at once.** Two unproven premises and two audio stacks, and no way to tell
which one is responsible when it sounds wrong.

**The Linux client first.** Accepted.

## Decision

The native Linux client is built first. It is where the person sits, where the
test in [ADR-VI-002](ADR-VI-002-our-own-realtime-client.md) actually happens,
and where echo cancellation is configuration rather than code. The Android
application is second, written against a tool contract that has already been
used in anger.

## Consequences

The premise gets tested on the cheaper of the two clients, and the phone client
inherits a surface that is known to work rather than one that was only designed.

What gets worse: the requirement that started this whole design — talking to the
agents from the phone — is the last thing delivered. If the Linux client is good
enough, there is a real risk the phone client is never written, and the honest
version of that is that it would have been the right outcome rather than a
failure.

## Related

[`docs/specification.md`](../docs/specification.md),
[ADR-VI-008](ADR-VI-008-a-native-client-on-each-device.md).
