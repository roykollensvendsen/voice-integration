# ADR-VI-008: A native client on each device, and no browser anywhere

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16. Superseded by [ADR-VI-018](ADR-VI-018-the-client-is-a-browser-page.md) the same day: the model that was actually wanted is reachable only over WebRTC, which a browser has and a native client would have to build.

## Context

Both the phone and the laptop carry a microphone, and the yardstick the person
set is explicit: as close as possible to the experience of GPT Live in the
ChatGPT app.

Three things decide how close a client gets, and they are not equally hard.

* **Full duplex, server-side turn detection and barge-in** are session settings
  on the Realtime API. Every client form gets them.
* **Acoustic echo cancellation** is not optional once the microphone is always
  open beside a speaker. Without it the model hears its own reply and answers
  it, and bills for both halves. A browser gets this free from `getUserMedia`;
  a native client brings its own.
* **A locked screen.** A browser tab loses the microphone when the phone locks
  or the person switches app. The ChatGPT app does not. This is the one place a
  browser loses on the phone, and it is exactly the case the person cares about:
  talking while walking.

## Options considered

**A browser client served by the bridge, on both devices.** One implementation,
free echo cancellation, no app to install, and on the laptop it is
indistinguishable from running GPT Live in a browser. Rejected on the phone, for
the locked screen, which is the case that motivated the phone at all.

**Browser on the laptop, native on the phone.** Keeps the free echo cancellation
where the speaker problem is worst and solves the locked screen where it
matters. Rejected: it would have meant the bridge serving static files and
minting client secrets, superseding
[ADR-VI-006](ADR-VI-006-no-runtime-dependencies.md), for one of the two clients.

**Native on both.** Accepted.

## Decision

An Android application on the phone, with a foreground service so the session
survives a locked screen, and a native client on the Arch laptop. No browser
client, and therefore no static file serving in the bridge.

## Consequences

[ADR-VI-006](ADR-VI-006-no-runtime-dependencies.md) survives: the bridge keeps
holding the key and nothing else, and the audio stacks live in the clients.

What gets worse, and it is the most expensive consequence in this repository:
echo cancellation is now ours twice. On Android it is `AcousticEchoCanceler`
from the audio effects API, which is per-device and not guaranteed present; on
Linux it is PipeWire's echo-cancel module, which is configuration on each
machine rather than code. Neither is written here, and both have to work before
either client is usable rather than merely annoying. The ten-minute test that
[ADR-VI-014](ADR-VI-014-the-linux-client-is-built-first.md) rests on is now a
weekend, and that was known when this was chosen.

## Related

[`docs/specification.md`](../docs/specification.md),
[ADR-VI-014](ADR-VI-014-the-linux-client-is-built-first.md).
