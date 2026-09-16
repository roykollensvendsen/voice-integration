# Decision records

A decision that costs more to reverse than to take is written down here before
the code that rests on it. A decision that only implements one already taken
is not; it is a commit message.

## The form

Every record is `ADR-VI-NNN-a-short-title.md`, with these sections in
this order:

| Section | Holds |
|---|---|
| Status | Accepted or Proposed, who decided, when; an objection returns it to Proposed |
| Context | what was true when the question arose, with sources where the facts are checkable |
| Options considered | every option weighed, including doing nothing, each with why it was not taken |
| Decision | what was chosen, in one paragraph |
| Consequences | what this costs, what it forecloses, and at least one thing that gets worse |
| Related | the pages it shapes |

Numbers are one sequence and never reused. A record is superseded by a later
one, never edited into a different decision.

Record the process choices too, not only the artefact ones. How a change is
made, and why, is what costs time on every future contribution, and it is the
decision nobody writes down.

## The records

| Id | Decides | Status |
|---|---|---|
| [001](ADR-VI-001-hermes-is-the-control-plane.md) | Hermes' gateway is the control plane; this repository builds only the voice edge | Accepted |
| [002](ADR-VI-002-our-own-realtime-client.md) | The voice layer is our own Realtime client, not the ChatGPT app | Accepted |
| [003](ADR-VI-003-the-voice-layer-can-only-narrow.md) | The voice layer can only ever narrow permissions | Accepted |
| [004](ADR-VI-004-identifiers-up-context-down.md) | Context flows down and identifiers flow up | Accepted |
| [005](ADR-VI-005-how-a-change-is-made.md) | Every fact stated twice is compared by something that can fail | Accepted |
| [006](ADR-VI-006-no-runtime-dependencies.md) | The bridge has no runtime dependencies | Accepted |
| [007](ADR-VI-007-mini-is-the-default-voice-model.md) | The mini model is the default, and the bill has a ceiling | Accepted |
| [008](ADR-VI-008-a-native-client-on-each-device.md) | A native client on each device, and no browser anywhere | Accepted |
| [009](ADR-VI-009-everything-runs-on-the-laptop.md) | Hermes and the bridge run on the laptop, reached over Tailscale | Accepted |
| [010](ADR-VI-010-one-live-microphone.md) | One live microphone, claimed rather than won | Accepted |
| [011](ADR-VI-011-the-device-is-the-identity.md) | The device is the identity; there is no voice identity | Accepted |
| [012](ADR-VI-012-an-agent-discussion-has-fixed-phases.md) | An agent discussion has fixed phases and then stops | Accepted |
| [013](ADR-VI-013-the-room-is-the-memory-scope.md) | The room is the memory scope | Accepted |
| [014](ADR-VI-014-the-linux-client-is-built-first.md) | The Linux client is built first, and it is evidence before it is a feature | Accepted |

What is deliberately left undone, and what would make each worth doing, is
[`deferred.md`](deferred.md). A thing left undone with no trigger is a thing
forgotten.
