# What is still unsettled

Five questions. Eleven stood here on 2026-09-16; six were decided that day and
moved into [`decisions/`](../decisions/README.md), where the answer is recorded
with what it cost. What is left is either a number nobody can pick yet or a fact
that can only be learned by building the thing.

The column that matters is the last one: what would settle it.

| # | The question | Why it is not a detail | What would settle it |
|---|---|---|---|
| 1 | What is the monthly ceiling, as a number? | [ADR-VI-007](../decisions/ADR-VI-007-mini-is-the-default-voice-model.md) says there is a ceiling and does not say what it is. A ceiling with no number is a wish, and the record is only half kept until it has one | Writing the first configuration file, which is when the number has to be typed |
| 2 | Does `AcousticEchoCanceler` work on the actual phone, at the rate the Realtime API wants? | Android's echo canceller is a per-device effect and is not guaranteed present. Without it the phone client is unusable rather than annoying, and no amount of the rest of this design helps | Building the Android client, which [ADR-VI-014](../decisions/ADR-VI-014-the-linux-client-is-built-first.md) puts second on purpose |
| 3 | Does PipeWire's echo-cancel module hold up with the laptop's speakers at normal volume? | Same failure on the other machine, and it is configuration rather than code, so it has to be written down per machine or it is lost on the next reinstall | Setting it up once and recording the configuration in this repository |
| 4 | Is the interaction, without the ChatGPT application around it, actually good enough? | [ADR-VI-002](../decisions/ADR-VI-002-our-own-realtime-client.md) rests on this and it has not been tested. If the answer is no, that record and much of this specification are wrong | Using the Linux client for a week, which is the whole reason it is built first |
| 5 | What does the client show so that holding the microphone is obvious? | [ADR-VI-010](../decisions/ADR-VI-010-one-live-microphone.md) makes the claim explicit and therefore makes forgetting it possible. Talking to a machine that is not listening is the failure this design invites | A first client, and watching the person forget |

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
| Browser or native | [ADR-VI-008](../decisions/ADR-VI-008-a-native-client-on-each-device.md) — native on both, and echo cancellation is therefore ours twice |

## How to read this page

A question that gets answered moves out of the first table and into a decision
record, with the answer and what it cost. A question that turns out to have been
the wrong question gets said so here rather than quietly deleted.

Nothing in the first table blocks building the Linux client, which is the point
of [ADR-VI-014](../decisions/ADR-VI-014-the-linux-client-is-built-first.md):
questions 1, 3, 4 and 5 are all answered *by* building it.
