# ADR-VI-003: The voice layer can only ever narrow permissions

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

The system is designed so a person can say "let Claude Code and DeepSeek look at
this, but not OpenCode", and so that `git commit` stops and asks. That is a
permission system driven by speech, and the question is how much authority the
speaking channel holds.

Speech is a channel with properties no other client has. It is used while
walking. It mistranscribes short words — the transcript this design came from
has "ikke la den committe" inside a sentence that meant the opposite. It is
audible to whoever is in the room, and anyone in the room can speak into it.
There is no second factor: the only evidence of identity is that a voice
happened.

Hermes accepts four answers to an approval: `once`, `session`, `always`, `deny`.
Two of them create standing permission.

## Options considered

**Give the voice layer the gateway's full authority.** Simplest, and matches
what a person expects when they say "just always let it commit". Rejected: the
failure is unbounded, deferred, and invisible — a permission granted by
mishearing is discovered by its consequences.

**Confirm dangerous answers by reading them back.** Better, and still inside the
same channel: a mishearing can be confirmed by a second mishearing, and the
person answering is still unidentified.

**Refuse standing permissions from voice; allow the per-call ones.** Accepted.

**Refuse all approvals from voice.** Safe and useless: answering approvals while
away from the desk is a large part of why the system exists.

## Decision

A voice session may answer `once` or `deny`, and nothing else. More broadly: the
voice layer has no mechanism for widening any permission — not for approvals,
not for its own tool surface, not for policy. Widening happens somewhere with a
screen.

## Consequences

A long run that trips the same approval repeatedly has to be answered
repeatedly, which is exactly the friction that makes people want `always`. The
person will hit this, and will be annoyed by it, and that is the trade.

The rule is enforced in `voice_bridge.policy`, marked `# RULE:` in the source,
rowed in `scripts/mutations.toml`, and proven by a test that goes red when the
rule is switched off. It also survives one layer down: the voice tool surface
does not offer `session` or `always` as values at all, so the model is never
told they exist.

## Related

[`docs/permissions.md`](../docs/permissions.md),
[`docs/voice-contract.md`](../docs/voice-contract.md).
