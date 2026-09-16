# What is still unsettled

Three questions. Eleven stood here on 2026-09-16; six were decided that day and
moved into [`decisions/`](../decisions/README.md), where the answer is recorded
with what it cost. What is left is either a number nobody can pick yet or a fact
that can only be learned by building the thing.

The column that matters is the last one: what would settle it.

| # | The question | Why it is not a detail | What would settle it |
|---|---|---|---|
| 1 | Does the browser's echo cancellation hold up with the laptop's speakers at normal volume? | Without it the model hears its own reply and answers it, and bills for both halves. `getUserMedia` provides it, which is not the same as it working in this room with these speakers | Opening the client and talking to it with the volume where you actually keep it |
| 2 | Is the interaction, without the ChatGPT application around it, actually good enough? | [ADR-VI-002](../decisions/ADR-VI-002-our-own-realtime-client.md) rests on this and it has not been tested. If the answer is no, that record and much of this specification are wrong | Using the Linux client for a week, which is the whole reason it is built first |
| 3 | What does the client show so that holding the microphone is obvious? | [ADR-VI-010](../decisions/ADR-VI-010-one-live-microphone.md) makes the claim explicit and therefore makes forgetting it possible. Talking to a machine that is not listening is the failure this design invites | A first client, and watching the person forget |

## What is no longer open, and where the answer went

| Was | Went to |
|---|---|
| Who pays for the audio | [ADR-VI-007](../decisions/ADR-VI-007-mini-is-the-default-voice-model.md) — mini by default, full model per session, a ceiling in configuration |
| The ChatGPT application or the interaction | [ADR-VI-014](../decisions/ADR-VI-014-the-linux-client-is-built-first.md) — tested on the Linux client before anything else is built |
| Where the bridge runs, and where the tools execute | [ADR-VI-009](../decisions/ADR-VI-009-everything-runs-on-the-laptop.md) — both on the laptop, reached over Tailscale, awake on mains power |
| Claude Code under a subscription | Answered by reading: `claude -p` works and draws from the subscription's own quota. The change that would have moved it to a metered credit pool was announced for 2026-06-15 and paused, which is a row in [`deferred.md`](../decisions/deferred.md) rather than a question |
| Who is allowed to speak | [ADR-VI-011](../decisions/ADR-VI-011-the-device-is-the-identity.md) — the unlocked device is the authentication, and it says what it does not protect |
| Audio that was never meant for the system | [ADR-VI-010](../decisions/ADR-VI-010-one-live-microphone.md) — the microphone is closed until a client claims it, which is not a setting but how it works |
| What stops an agent discussion | [ADR-VI-012](../decisions/ADR-VI-012-an-agent-discussion-has-fixed-phases.md) — three phases, then it stops whether or not they agree |
| The memory scope | [ADR-VI-013](../decisions/ADR-VI-013-the-room-is-the-memory-scope.md) — the room is the scope |
| Which microphone is live | [ADR-VI-010](../decisions/ADR-VI-010-one-live-microphone.md) — one, claimed by a gesture on the device |
| Browser or native | [ADR-VI-018](../decisions/ADR-VI-018-the-client-is-a-browser-page.md) — a browser page, because `gpt-live-1` is reachable over WebRTC only and a browser has WebRTC and echo cancellation already |
| Which model, and what it costs | [ADR-VI-017](../decisions/ADR-VI-017-the-voice-model-is-gpt-live-1.md) — `gpt-live-1`, flat at $0.05 a minute billed per second |
| The monthly ceiling | $20, which is 400 minutes. `voice_bridge.budget` refuses a session once the month is spent |

## How to read this page

A question that gets answered moves out of the first table and into a decision
record, with the answer and what it cost. A question that turns out to have been
the wrong question gets said so here rather than quietly deleted.

Nothing in the first table blocks building the client, which is the point of
[ADR-VI-014](../decisions/ADR-VI-014-the-linux-client-is-built-first.md): every
one of the three is answered *by* building it.
