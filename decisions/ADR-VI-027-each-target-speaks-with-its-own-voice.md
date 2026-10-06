# ADR-VI-027: Each target speaks with its own voice

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-06.

## Context

[ADR-VI-026](ADR-VI-026-you-choose-who-you-talk-to.md) let the person choose who
a turn goes to: the voice alone, the gateway, or one Claude Code session. All
three answered in the same voice. Its own warning was that a forgotten choice
sends the next question somewhere nobody meant, and that a line on the screen
was the only guard. A screen is no guard for somebody walking with the phone in
a pocket.

The person proposed the fix: if the voice only carries another agent's answer,
it is better to hear that agent's own voice. They also asked to hear which
voices there are and to pick one by saying so.

`gpt-live-1` sets its voice when a session opens, and "start a new session to
change it" is the vendor's own instruction. Fourteen names are accepted, checked
by calling the API:
[`evidence/api/gpt-live-1-transport-and-delegation.md`](../evidence/api/gpt-live-1-transport-and-delegation.md).

## Options considered

**One voice, and the target said aloud on every answer.** "Hermes says: …".
Rejected: it is said on every turn, it costs time on every turn, and people stop
hearing a prefix after the third time.

**A text-to-speech pass for answers from somewhere else.** The agent's answer is
spoken by a separate speech model in its own voice. Rejected: a second paid model
on every answer, and two voices that cannot hear each other talking over one
another.

**One voice per kind of target, and a new session when it changes.** Accepted.

## Decision

The voice alone, the gateway and a Claude Code session each have a voice,
`marin`, `cedar` and `quartz` unless the person picks others. The voice for the
chosen target is set when a session opens. When the target changes to one with a
different voice, the page closes the session and opens a new one. The
conversation so far is handed to the new session, as it already is when a
session is reopened.

"Which voices are there" is answered with the names. "Change the voice to …"
sets the voice for the target that is chosen now. So does a control on the page.
Only a name the service accepts is ever sent.

## Consequences

The person hears who is answering, without being told.

What gets worse: changing target now costs a reconnect. That is a pause of about
a second or two before the next turn can be heard, and the voice briefly forgets
anything not yet passed back as history. Within one target nothing changes.

## Related

[ADR-VI-017](ADR-VI-017-the-voice-model-is-gpt-live-1.md),
[`docs/voice-contract.md`](../docs/voice-contract.md).
