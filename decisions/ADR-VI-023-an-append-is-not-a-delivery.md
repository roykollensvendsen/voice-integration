# ADR-VI-023: An append is not a delivery

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-17. Extends
[ADR-VI-019](ADR-VI-019-a-delegation-not-a-tool-list.md).

## Context

The answer reached the screen and did not reach the voice. The clock and the
position came back in under a millisecond, were drawn in the conversation, and
the voice went on as though it had been told nothing — then delegated the same
question again, and the gateway ran `date` to answer what the bridge had already
answered.

Three things could produce that, and from the outside they look identical: the
page never sent the answer, the voice plane never received it, or it received it
and chose to stay quiet. They need different fixes, and there was no way to tell
them apart. The page sent `session.commentary.append` and moved on. Nothing was
watched, nothing was recorded, and the second hop — page to voice — happens
where the bridge cannot see it.

There is a signal, and it was being ignored. Every append is acknowledged with
`session.commentary.appended`, carrying the `event_id` it was sent under. The
guide is careful that this is not proof the model spoke anything, which is true
and was read as a reason to ignore it. It is still the only sign that the voice
plane received anything at all.

Then a screenshot settled what was actually happening, and it was worse than a
dropped message. Asked "do you have my position now", the voice said no — while
the page beside it displayed *Harebakken, Arendal, Norge*, which the bridge had
resolved minutes earlier. It had not asked anybody. "Do you have X" reads as a
question about itself, and questions about itself are exactly the ones it is
told to answer alone. It was right about itself and wrong about the system, and
no instruction to go and ask can help: it did not think there was anything to
ask about.

The other half is timing. The page said "on it" the moment a delegation arrived,
then the answer — which was written when everything took ten seconds. Since
[ADR-VI-022](ADR-VI-022-a-short-path-past-the-control-plane.md) some answers
take one millisecond, so both arrived together: two things to paraphrase, a few
milliseconds apart, of which only the second mattered.

## Options considered

**Wait for the model to speak.** There is no event for it. Output transcript
deltas arrive, but nothing ties one to the append that caused it.

**Append once and hope.** What was there. It fails silently, which is how this
went unnoticed through several conversations.

**Watch the acknowledgement.** Accepted.

## Decision

Every append goes through one function, which keeps the `event_id` and waits
`ACKNOWLEDGED_WITHIN_MS` for the acknowledgement. Nothing back, and the answer
is said once more; nothing back again, and that is reported rather than
dropped. Both outcomes go to the bridge over `POST /noticed` and appear in the
watch stream, so a conversation that went wrong can be read afterwards instead
of reconstructed from what somebody remembers hearing.

What the page may report is a closed list. The bridge acts on some event names,
and a page that could report an approval request could make the bridge believe a
permission question is open when none is.

The holding line waits `HOLD_AFTER_MS` before it is said at all. It exists
because silence sounds like a dropped call; where there is no silence there is
nothing for it to cover.

And where the person is, the voice is simply told. `session.thinking.append`
carries a fact the model should have and not read out, which is what this is:
the moment the browser gives a position and the bridge turns it into a name, the
page passes the name on. The voice then answers from something it holds, rather
than being asked to go and fetch what it does not believe exists.

## Consequences

A dropped append now costs a repeat rather than the whole answer, and the
failure leaves a record. The record is the larger part: the page is the only
witness to what the voice plane did, and it now testifies.

The cost is that the page is trusted a little further than before. It already
held the transcript; it now writes rows into the watch stream that a person
reads as fact. The closed list keeps that from reaching anything the bridge acts
on, and the reports themselves are not acted on at all.

Pushing a fact rather than fetching one is a pattern with a limit. It works for
the position because there is one of them, it is small, and it changes rarely.
It does not generalise to the clock or to anything the gateway knows: a fact
pushed into the session is a fact that can go stale there with nothing to
correct it. The list of things told this way should stay at one for as long as
possible.

A repeat can also be heard twice, if the acknowledgement was merely late rather
than absent. Two and a half seconds is the guess that makes that unlikely, and
it is a guess: nothing in the guide says how long an acknowledgement takes.
Hearing an answer twice is the better failure of the two.

## Related

[ADR-VI-019](ADR-VI-019-a-delegation-not-a-tool-list.md),
[ADR-VI-022](ADR-VI-022-a-short-path-past-the-control-plane.md).
