# ADR-VI-032: The phone app starts as the page in a wrapper, kept alive with the screen off

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-09.

## Context

The voice is a browser page. On the phone it stops listening the moment the
screen locks or the browser goes to the background, which is the moment the
phone goes into a pocket. Roy asked for a voice that keeps going in the pocket,
and later for a wake word, podcasts that pause around it, and calling people by
name ([the proposal](../docs/phone-app-proposal.md)). His phone is an Android
phone.

All the behaviour of the voice lives in the page:
- the voice session and the delegation to the bridge;
- the acknowledgements, the news and the timings.

That is several hundred lines tested in real conversations.

## Options considered

**Rewrite the page natively.** Every behaviour in Kotlin, with a native
WebRTC library. Rejected for the first step: weeks of work to arrive where the
page already is, with two copies of the same behaviour to keep in step.

**The page in a wrapper.** A small app that shows the page in Android's own
browser view, holds a background service of the kind Android allows for a
microphone, and keeps the screen-off phone from pausing it. Accepted.

## Decision

The first version of the phone app is today's page, unchanged, inside a thin
Android app. It loads the page the bridge already serves over Tailscale, and
adds only what a page cannot have:
- a foreground service of type microphone, with its notification, started
  while the app is on screen as Android requires;
- a wake lock, so audio carries on with the screen off;
- the microphone permission granted to the page.

The talk button stays a button: ADR-VI-010 is untouched until the wake word,
step two of the proposal, which will amend it in its own record.

## Consequences

Everything learnt in the page carries over the same day, and a fix to the page
is a fix to the app. The cost is that the app depends on the bridge being
reachable over Tailscale, exactly as the page does.

Native work is added only where the page cannot follow:
- the wake word;
- media controls;
- contacts and calls.

It is not added where the page already works.

## Related

[ADR-VI-010](ADR-VI-010-one-live-microphone.md),
[ADR-VI-018](ADR-VI-018-the-client-is-a-browser-page.md),
[`docs/phone-app-proposal.md`](../docs/phone-app-proposal.md).
