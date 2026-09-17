# ADR-VI-022: A short path past the control plane, for questions it owns

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-17. A deliberate hole in
[ADR-VI-001](ADR-VI-001-hermes-is-the-control-plane.md).

## Context

Every spoken request went to the gateway. The gateway sends thirty-three
thousand tokens of its own preamble — system prompt, twenty-three tool
definitions, a catalogue of sixty-two skills — before it reads a word of the
question. Measured: twelve seconds to be told the time, and the same cost for
"what is two plus two" as for a real piece of work.

Someone looking at this design from outside put it plainly: every question has
to go to the orchestrator to be interpreted before anything can happen, which
is several models in series, more latency and more places to fail. They
suggested giving the voice model a few tools of its own.

That last part is not available.
[ADR-VI-019](ADR-VI-019-a-delegation-not-a-tool-list.md) chose client
delegation, in which `gpt-live-1` is given no functions at all; and the
vendor's own description is that the voice model "listens, speaks, and decides
when to ask the backend", while "the backend reasons, uses tools". It is not a
tool-calling model in either mode. Suggesting otherwise describes the Realtime
API, which [ADR-VI-017](ADR-VI-017-the-voice-model-is-gpt-live-1.md) rejected.

But the bridge sees every delegation before the gateway does, and for a few
questions the bridge is the authority rather than a guesser: it keeps the
clock's process, it writes the spend ledger, and it follows the run stream.

## Options considered

**Leave it.** Twelve seconds for the time is survivable, and every rule stays
whole. Rejected: it is the single most noticeable thing about using the system,
and the cost buys nothing.

**Make the gateway cheaper** — fewer tools, a shorter skill catalogue for this
profile. Worth doing regardless, and it does not get near a millisecond. Kept as
a later job rather than an alternative.

**Answer a short list at the bridge.** Accepted.

## Decision

The bridge answers five kinds of question itself and sends everything else on.

Three it simply knows, in under a millisecond: the time, what is left of the
month, and whether anything is running. Only a question shorter than sixty
characters qualifies, so a long question containing the word "time" still
travels.

Two it fetches. Where the person is, from coordinates the browser was allowed to
give, turned into a name somebody can say. And what the web says, through one
search call rather than an agent — six seconds rather than twelve, and no
repository is read to answer who won a motor race.

## Consequences

The system stops feeling slow for the things people ask most often, and the
answers are better as well as faster: the bridge is not guessing what it spent,
it is reading its own ledger.

What gets worse is the rule. ADR-VI-001 said the gateway decides, so that three
harnesses would not each have to be trusted to behave; this is a second place
where a decision is made, and it is a place with no permission layer because it
never touches anything. The list stays short for exactly that reason, and adding
to it is a decision rather than a commit.

The position is the part that needs watching. It is asked for once when the
microphone is taken, by the browser, of the person; it is held in this process
and written nowhere; and declining is answered with "I do not know where you
are" rather than a guess. None of that makes it less sensitive, and it is the
first thing here that would matter if the bridge were ever reachable by somebody
else.

The other cost is a wrong answer given confidently. A question matching one of
these phrases is answered here even if the person meant something else, and
they get a fast wrong answer instead of a slow right one. The length limit is
the only guard, and it is crude.

## Related

[ADR-VI-001](ADR-VI-001-hermes-is-the-control-plane.md),
[ADR-VI-019](ADR-VI-019-a-delegation-not-a-tool-list.md).
