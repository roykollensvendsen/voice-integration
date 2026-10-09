# ADR-VI-033: A spoken wake word may open the microphone

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-09. Amends
[ADR-VI-010](ADR-VI-010-one-live-microphone.md).

## Context

ADR-VI-010 says the microphone opens only on a deliberate act: a key or a
button. With the phone app
([ADR-VI-032](ADR-VI-032-the-phone-app-starts-as-the-page-in-a-wrapper.md))
the voice goes into a pocket, where nobody presses a button. Roy asked to start
the voice by speaking to it, and for it to cost nothing until then. He chose
"Hey Jarvis" as the first wake word.

The paid voice session cannot do the listening itself: it bills for every
second it is open. And a television, a podcast or another person could say
something close to the word.

## Options considered

**Keep the button.** Rejected: the button is the reason the voice stays in the
pocket unused.

**Listen with the paid session, always open.** Rejected: it bills all day, and
it would send everything said near the phone to the voice service.

**A small detector on the phone listens for one word.** Accepted.

## Decision

Saying the wake word counts as the deliberate act. Three rules keep that safe:

* **The detector runs on the phone, and sends nothing.** It is a small model,
  openWakeWord's, that hears only whether the word was said. No audio leaves the
  phone until it has been.
* **A false start costs at most one short session.** A session the word opened
  closes by itself after a quiet spell, and the detector listens again.
* **One microphone at a time still holds.** While a session is open, the
  detector does not listen, and the button still works as before.

## Consequences

The voice can be woken in a pocket, and costs nothing until it is. The cost is
that something which sounds like the word can open a session. That is bounded
by the quiet spell, and the session's notification on the phone shows it is
open.

The first word is English, "Hey Jarvis", because a ready model exists. A
Norwegian word needs a model trained for it, and is a later change.

## Related

[ADR-VI-010](ADR-VI-010-one-live-microphone.md),
[ADR-VI-032](ADR-VI-032-the-phone-app-starts-as-the-page-in-a-wrapper.md),
[`docs/phone-app-proposal.md`](../docs/phone-app-proposal.md).
