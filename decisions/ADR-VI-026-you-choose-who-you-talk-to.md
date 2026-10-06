# ADR-VI-026: You choose who you talk to, and the choice stays until you change it

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-06. Designed together with the
session that maintains claude-voice.

## Context

Every spoken request the voice could not answer itself went to the gateway, the
planning agent. That is the right place for a request that needs planning. It is
the wrong place for a conversation with one Claude Code session that is already
running: the gateway is a paid model call of about ten seconds, and it has to
work out from scratch, every turn, which session was meant.

The person put the reason in two words: cost and response. Talking to the voice
alone is free and instant. Talking to the gateway costs a model call. Talking
to one session through
[claude-voice](https://github.com/roykollensvendsen/claude-voice) costs nothing
extra on the subscription and answers in about five seconds, measured on
2026-10-06.

And they asked for a picture: the sessions as a tree, with the one being spoken
to picked by a tap as easily as by a sentence.

## Options considered

**Let the gateway route.** It already has the claude-voice tools
([ADR-VI-025](ADR-VI-025-a-running-session-is-reached-through-claude-voice.md)).
Rejected as the only path: it puts a model call in front of every sentence,
which is exactly the cost the person wants to be able to avoid.

**Name the session in every sentence.** "Tell the build session …" each time.
Rejected: it is how you talk to a dispatcher, not to the person you are talking
to. Once chosen, a session should be spoken to as if it were the only one.

**A chosen target, kept by the bridge.** Accepted.

## Decision

The bridge keeps one target: the voice alone, the gateway, or one named Claude
Code session. It keeps it on disk, so a restart or a dropped call does not lose
it. A spoken turn that the bridge cannot answer itself goes to the target and
nowhere else. With the voice alone, nothing is forwarded at all.

The target changes two ways. Tapping a node in a tree of the running sessions on
the page, or saying "talk to …" with a name or a project. A spoken name switches
only when it matches exactly one running session; otherwise the voice asks which.

News and permission questions come first whatever the target is
([ADR-VI-024](ADR-VI-024-coding-sessions-are-heard-from-claude-voice.md)): a
"yes" still answers the request that is waiting, not the chosen session.

When the chosen session ends, the target goes back to the voice and the voice
says so. A session waiting for somebody at its own screen is reported and stays
chosen, since the person may be standing at that screen.

## Consequences

A conversation with one session is a conversation: about five seconds a turn,
nothing billed beyond the subscription, and no planner deciding what was meant.

The bridge's list of claude-voice tools grows from three to six: listing the
running sessions, asking one, and reading what one wrote since a given turn.
Each is a read or a message, never a permission.

What gets worse: a forgotten target is a trap. Somebody who chose a session an
hour ago and asks the time gets the time, because the clock never travels, but
somebody who asks "what is on the calendar" sends that to a coding session. The
target is therefore shown at the top of the page at all times, and the voice is
told quietly which target is chosen whenever it changes.

## Related

[`docs/claude-voice-contract.md`](../docs/claude-voice-contract.md),
[`docs/voice-contract.md`](../docs/voice-contract.md),
[ADR-VI-022](ADR-VI-022-a-short-path-past-the-control-plane.md).
