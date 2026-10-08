# ADR-VI-031: Every turn is traced and measured, and kept long enough to compare weeks

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-08.

## Context

On 2026-10-06 the bridge was stopped for lack of memory and the page answered
502 until somebody noticed. Nothing had warned anybody, and nothing recorded
it. Every problem found in these two days was found because the person heard it
go wrong and asked for the log of the last conversation. That log is a list of
events in memory, gone at the next restart, and it cannot say whether this week
went better than the last.

The person asked for three things on top of that. The same numbers should be
visible on the page, not only in logs. An assistant should be able to diagnose
the bridge from one summary rather than reading transcripts. And whatever must
interrupt, such as memory running low, must be pushed rather than waiting to be
asked for, because nobody asks a dying process how it is.

## Options considered

**Log lines only, read with journalctl.** Rejected: nothing to compare across
weeks, and nothing the page or the voice can read.

**A metrics service** (Prometheus and a dashboard). Rejected: two more programs
to run on a laptop that just ran out of memory, for one person's numbers.

**One small store in the bridge, read three ways.** Accepted.

## Decision

Every spoken turn gets a trace id, and it travels with every call the turn
makes, including into claude-voice, so one search follows a turn end to end.
The bridge writes one structured log line per event. It also keeps a few
numbers in an SQLite file in its state directory for ninety days:

* restarts, and how long until the bridge answered again;
* how long a turn took, from the request to the answer;
* latency and errors per tool;
* how each turn ended;
* how often an answer had to be cut.

The page reads a summary from a plain address on the bridge. The voice answers
"how has the bridge been doing" from the same summary, without a model call.
Anything that should interrupt is pushed, never polled.

## Consequences

A bad week shows up as a number next to last week's, not as a vague feeling
that the voice has been worse lately.

What gets worse: one more file, which grows until it is pruned. It holds no
words, only names, timings and outcomes, so it says what happened but not what
was said.

## Related

[ADR-VI-029](ADR-VI-029-the-bridge-owns-every-open-request.md),
[`docs/specification.md`](../docs/specification.md).
