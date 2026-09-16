# ADR-VI-011: The device is the identity

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

The bridge knows a voice session. It does not know a person. Anyone standing at
an unlocked laptop, or near a phone lying face up, can say "stop that run" or
answer an approval.

[ADR-VI-003](ADR-VI-003-the-voice-layer-can-only-narrow.md) already bounds the
damage: a voice session may answer `once` or `deny` and can never grant standing
permission. That is a mitigation and not an answer.

## Options considered

**Speaker verification.** A model recognises the person and refuses everyone
else, which is the actual problem solved. Rejected: a false rejection when the
person has a cold or is standing in wind is annoying in the particular way that
gets a security control switched off, and a false acceptance is silent. It is
also another model in the chain, on a system whose whole argument is that the
voice layer should be thin.

**A spoken passphrase for dangerous actions.** Rejected, and it was argued
against when it was offered: a passphrase said out loud is heard by the room,
and after the third time it is not a secret.

**The device is the identity.** Accepted.

## Decision

There is no voice identity. Claiming the microphone
([ADR-VI-010](ADR-VI-010-one-live-microphone.md)) requires a gesture on an
unlocked device, and the unlocked device is the authentication — the same model
the rest of the phone runs on.

## Consequences

Nothing to build, nothing to tune, and no control that quietly stops working.
The boundary is the one the person already maintains when they lock their
screen.

What gets worse, stated plainly rather than hidden: this does not protect
against somebody at the open machine. It is the reason rooms with more than one
person are the last phase and not the second, and the reason
[ADR-VI-003](ADR-VI-003-the-voice-layer-can-only-narrow.md)'s limit on approval
answers carries more weight than it otherwise would.

## Related

[`docs/permissions.md`](../docs/permissions.md),
[`decisions/deferred.md`](deferred.md).
