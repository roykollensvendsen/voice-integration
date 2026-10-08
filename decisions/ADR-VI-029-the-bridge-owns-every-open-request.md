# ADR-VI-029: The bridge owns every open request, and nothing is lost when the microphone is down

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-06.

## Context

The person's first voice assistant lost work when a phone call interrupted it.
They asked for four things to hold across this whole chain, and two did not:

* **Every request reaches an end.** Done, failed or given up on, and said so,
  never silence. Here the page waited a quarter of an hour for a slow answer,
  then wrote "gave up" on the screen and said nothing.
* **Open requests live in the bridge, not in the voice session.** Here news that
  arrived while the microphone was down was shown on the screen and never said.
  An answer that came after the page stopped waiting went nowhere. And the
  bridge kept its place in claude-voice's news in memory, so a restart started
  the news over from now and dropped whatever had happened in between.

The page is the wrong owner for any of this. It can be closed, reloaded or
asleep in a pocket. The bridge runs for as long as the laptop does.

## Options considered

**Leave it to the page.** It already keeps the conversation on screen.
Rejected: a page that is not open owns nothing.

**Keep everything in claude-voice.** It already keeps its own news.
Rejected: half of what can be missed comes from the gateway, which claude-voice
never sees.

**The bridge keeps what was said and what was heard, on disk.** Accepted.

## Decision

The bridge keeps three things in a state file beside the target: its place in
claude-voice's news, the news worth saying aloud, and how far the person has
heard it.

The page reports each piece of news it says aloud. When the microphone is taken
again, what was not heard is said first, briefly, as "while you were away".

An answer from the gateway that arrives when no page is waiting for it becomes
news, so it is heard like any other. A page that has waited as long as it will
says so aloud, and says that the answer will come as news.

## Consequences

A dropped call, a locked phone or a bridge restart loses nothing that was worth
saying. It is said later instead.

What gets worse: "while you were away" can be long after a busy afternoon. Only
the latest few items are said; the rest is counted and left on the screen. And
the state file is one more thing on disk that holds what sessions said. It is
kept to what would have been spoken anyway.

## Related

[ADR-VI-024](ADR-VI-024-coding-sessions-are-heard-from-claude-voice.md),
[ADR-VI-023](ADR-VI-023-an-append-is-not-a-delivery.md).
