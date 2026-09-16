# ADR-VI-013: The room is the memory scope

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

Hermes separates two identifiers. `session_id` is the conversation — what this
specification calls a room. `X-Hermes-Session-Key` is the long-term memory
scope. They do not have to follow each other.

Sharing gives continuity: something said to the phone is known by the agent in
the terminal afterwards, which is a large part of why the system is worth
having. Sharing also means anything said out loud, in a room with other people
in it, is remembered by everything else.

## Options considered

**One scope for the whole system.** Maximum continuity; the agents know
everything regardless of where it was said. Rejected: there is then no way to
say anything without it being remembered everywhere, and no way to keep an
experiment out of the work.

**A separate scope for voice.** Nothing said aloud ever reaches the typed
sessions' memory. Safest against a conversation in a room leaking into the work,
and it removes the thing that was asked for: start a job by speaking and follow
it up in the terminal.

**The room is the scope.** Accepted.

## Decision

`X-Hermes-Session-Key` is set to the room. Voice and typed sessions in the same
room share memory; different rooms share none.

## Consequences

Continuity where it was wanted, and a boundary the person can draw themselves
without learning a second concept — the room was already the unit the phone and
the laptop share.

What gets worse: drawing that boundary is a deliberate act. Someone who never
changes room has one scope after all, and will be surprised the first time an
agent recalls something said in a different context. There is no mechanism that
reminds them, and a reminder would be noise on every other turn.

## Related

[`docs/specification.md`](../docs/specification.md),
[`docs/hermes-contract.md`](../docs/hermes-contract.md).
