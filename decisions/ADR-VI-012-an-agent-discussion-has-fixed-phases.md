# ADR-VI-012: An agent discussion has fixed phases and then stops

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

Letting two agents argue was asked for explicitly, and described precisely: each
makes an independent analysis, then each criticises the other's, then they give
one joint conclusion.

Two agents arguing is two token streams with no natural end, and neither of them
notices that it got expensive. The cost also lands somewhere the audio ceiling in
[ADR-VI-007](ADR-VI-007-mini-is-the-default-voice-model.md) cannot see: Claude
Code's subscription quota, and the DeepSeek and OpenCode bills.

## Options considered

**A token budget per discussion.** They argue freely until the budget runs out,
then a conclusion is forced. More flexible — an easy disagreement settles in two
rounds and a hard one gets ten. Rejected: a budget measured in tokens is
difficult to have an opinion about beforehand, so the number would be guessed
and only judged afterwards.

**A person approving each round.** Safest, and it destroys the point: the reason
to set two agents on a question is to be doing something else.

**The shape is the bound.** Accepted.

## Decision

A discussion has exactly three phases: one independent analysis each, one round
of criticism each, one joint conclusion. Then it stops, agreed or not. More
rounds happen only because the person asks for them.

## Consequences

The cost of a discussion is known before it starts, and the transcript has a
shape that can be read afterwards rather than being an argument to scroll
through.

What gets worse: a genuinely hard disagreement is cut off at the point where it
was getting interesting, and the person has to notice and ask for more. That is
the trade, and the alternative was a number nobody could have chosen well.

## Related

[`docs/specification.md`](../docs/specification.md),
[`decisions/deferred.md`](deferred.md).
