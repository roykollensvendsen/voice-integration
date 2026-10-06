# ADR-VI-028: New work goes to a session you can see, never to a hidden Claude

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-06. Supersedes
[ADR-VI-021](ADR-VI-021-a-resumable-print-session.md), and completes
[ADR-VI-025](ADR-VI-025-a-running-session-is-reached-through-claude-voice.md).

## Context

[ADR-VI-021](ADR-VI-021-a-resumable-print-session.md) had the gateway reach
Claude Code as `claude -p`: a one-off question in print mode, resumed by
identifier. It worked, and it was the only way the gateway had.

Since then everything else in this system has come to rest on claude-voice.
News that a session finished, permission questions, the tree of sessions on the
page, and talking to one session directly all go through it
([ADR-VI-024](ADR-VI-024-coding-sessions-are-heard-from-claude-voice.md),
[ADR-VI-026](ADR-VI-026-you-choose-who-you-talk-to.md)). A `claude -p` run is
outside all of it. It is not in the tree, it sends no news when it finishes, and
it cannot stop to ask for permission. The person asked the obvious question: why
would the gateway use it at all?

## Options considered

**Keep print mode for new questions.** Rejected: it is the one kind of work the
person can neither see nor hear from.

**Start a new session for every request.** Rejected: sessions pile up, and each
one reads the project again from nothing.

**Reuse a session in the project, or start one, and hand it the work.**
Accepted.

## Decision

New work in a repository goes to a session the gateway started there before,
or to a new one it starts with claude-voice's `create_session`. It is handed
over with `send_task`. The gateway does not wait: it says in one sentence what
it started and where. The session itself is heard from when it finishes or
needs permission. The gateway never runs `claude -p`, or any other coding agent,
from a terminal.

## Consequences

Every piece of work is in the tree, can be chosen and spoken to directly, and
reports back on its own.

What gets worse: a voice turn that starts work no longer ends with the result.
The answer arrives later, as news. And the sessions the gateway starts are run
by claude-voice itself. Today the bridge cannot choose those as a target, so
following up on one goes through the gateway until it can.

## Related

[`docs/hermes-contract.md`](../docs/hermes-contract.md).
