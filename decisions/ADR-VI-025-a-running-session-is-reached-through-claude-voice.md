# ADR-VI-025: A running session is reached through claude-voice, not a fresh Claude

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-06. Narrows
[ADR-VI-021](ADR-VI-021-a-resumable-print-session.md) to new questions.

## Context

[ADR-VI-021](ADR-VI-021-a-resumable-print-session.md) told the gateway to reach
a coding agent with `claude -p`, resuming the same print session for every later
question. That was the only way it had.

It now has another. On 2026-10-06 the gateway was given the tools of
[claude-voice](https://github.com/roykollensvendsen/claude-voice), the server on
this laptop that runs and watches Claude Code sessions. It can list the sessions,
send one a message, read what one wrote, and summarise one.

The instruction still said print mode, and the gateway did as it was told.
Asked by voice to list the Claude Code sessions, it started a new `claude -p` to
go and look. It asked for "Ja, kjør claude" before it did. Then it said it had
used the session server, which it had never touched.

## Options considered

**Leave the instruction alone.** The tools are there, and a model may find them.
Rejected: it was handed a sentence telling it how to reach a coding agent, and
it followed the sentence.

**Drop print mode altogether.** Everything goes through claude-voice, which can
also start a session. Rejected for now: print mode works, it measured reliable,
and a question about a repository with nothing running does not need a session
somebody will see in a list later.

**Say which is which.** Accepted.

## Decision

The instruction sent with every voice turn says that listing the sessions, or
asking, telling or reading one that is already running, goes through the
claude-voice tools, and never through a new `claude -p`. Listing and reading
change nothing, so they are done without asking first. Print mode stays for a new
question in a repository where no session is running.

## Consequences

"List the sessions" names the sessions that are actually running, and "tell
the build session to rerun the tests" reaches the build session.

What gets worse: two ways to reach Claude, and the gateway decides which. A
question about a repository that has a session running somewhere may now go to
that session, mid-task, rather than to a fresh one. Whether that is welcome
depends on what the session was doing.

## Related

[ADR-VI-024](ADR-VI-024-coding-sessions-are-heard-from-claude-voice.md),
[`docs/hermes-contract.md`](../docs/hermes-contract.md).
