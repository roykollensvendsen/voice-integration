# ADR-VI-019: The voice model gets a delegation, not a tool list

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16. Supersedes the framing of
[`docs/voice-contract.md`](../docs/voice-contract.md), not a numbered record.

## Context

Every version of this design so far assumed the voice model is handed six
function definitions and decides which to call. That is how the Realtime API
works, and it is what
[ADR-VI-004](ADR-VI-004-identifiers-up-context-down.md) was written against.

`gpt-live-1` offers two ways to reach a backend, and neither is that.

**Responses delegation** registers functions in `delegation.responses.tools`.
OpenAI runs a backend model of their choosing, that model selects a function,
and the application executes it. The six-function surface survives intact.

**Client delegation** is set with `{"delegation": {"type": "client"}}`. The Live
session then "does not configure or run those backend tools" at all. When the
model wants help it emits `session.delegation.created` carrying an opaque id and
nothing else — explicitly "metadata, not task text". The application keeps the
transcript from `session.input_transcript.delta`, works out what was wanted,
does the work, and returns a string with `session.commentary.append` for the
model to paraphrase aloud, or `session.thinking.append` to inform it silently.

## Options considered

**Responses delegation.** Keeps the contract this project already wrote and
tested. Rejected: it puts an OpenAI model in the planning seat, which is the one
seat [ADR-VI-001](ADR-VI-001-hermes-is-the-control-plane.md) gave to Hermes. It
is also a second metered model on the critical path of every sentence, against
[ADR-VI-004](ADR-VI-004-identifiers-up-context-down.md).

**Client delegation.** Accepted.

## Decision

The session is created with client delegation. The voice model is given no
functions. The bridge keeps the transcript, answers each delegation by asking
Hermes, and appends the reply as commentary.

The six entries in [`docs/voice-contract.md`](../docs/voice-contract.md) remain,
and stop being a surface handed to a model. They become the bridge's own
vocabulary: the only six things it will do when a delegation arrives, and
therefore still the boundary
[`docs/permissions.md`](../docs/permissions.md) describes.

## Consequences

The architecture gets simpler and more honest. There is no model outside this
machine choosing what happens to a repository; there is a transcript, a gateway
that plans, and six things the bridge is willing to do. The vendor's own
sentence — the application "manages task state and enforces permissions and
required confirmations" — is now literally true here rather than approximately.

What gets worse, and it is not small. Transcript handling becomes ours. The
guide is blunt that "a transcript fragment is not a complete user turn, and
transcripts may contain mistakes", so the bridge now owns a problem the function
surface used to hide: deciding when someone has finished asking for something,
and what they meant when they said "yes" or "Thursday, not Friday". That is a
whole class of bug this design did not have an hour ago.

An append is also not a receipt: the guide says an acknowledgment "is not proof
that the model has consumed or spoken the result, or that an external action
succeeded". So the person can be told nothing while something has already run,
which makes the approval flow more important and less observable.

## Related

[`docs/voice-contract.md`](../docs/voice-contract.md),
[ADR-VI-017](ADR-VI-017-the-voice-model-is-gpt-live-1.md).
