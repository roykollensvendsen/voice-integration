# ADR-VI-010: One live microphone, claimed rather than won

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

Two always-open microphones on one room is not the same problem as two screens.
A sentence spoken in front of both is answered twice. Both sessions bill while
idle. Two sessions that both heard "run the tests" start the work twice.

And the common case is the worst one: the phone lying on the desk beside the
laptop, both microphones hearing the same room.

Worth noticing: the ChatGPT app already solves this, and solves it this way. A
person opens voice mode on one device. The other is not listening.

## Options considered

**Last speaker wins.** The client that hears speech takes over. Frictionless
when it works — walk up to a machine and talk. Rejected: a television, a
podcast or another person can take the microphone, and when both machines hear
the same sentence which one wins is a race.

**Both live at once.** Nothing to build. Rejected: the person hears every answer
twice, pays idle on two sessions, and can start one job twice.

**An explicit claim.** Accepted.

## Decision

At most one client holds the microphone. Taking it is a deliberate act — a key
on the laptop, a button in the application — and the other client drops to the
screen and stops listening. Which client is live is a fact stored on the room,
not the outcome of a race.

## Consequences

It answers a second question for free, and answers it better than a setting
would: the microphone is closed until someone claims it. "When is this thing
listening?" has the answer "when you said so", which is a sentence a person can
actually rely on.

What gets worse: every move between desk and phone costs a gesture, and the
person will forget it and talk to a machine that is not listening. The client
has to make holding the microphone visible enough that the mistake is obvious,
and that is user interface work nobody has scoped.

## Related

[`docs/specification.md`](../docs/specification.md),
[`docs/permissions.md`](../docs/permissions.md).
