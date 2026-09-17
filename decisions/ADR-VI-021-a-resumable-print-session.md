# ADR-VI-021: Talk to a coding agent over a resumable print session

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-17. Supersedes
[ADR-VI-020](ADR-VI-020-print-mode-not-a-screen.md), whose reasoning holds and
whose main cost turns out not to exist.

## Context

[ADR-VI-020](ADR-VI-020-print-mode-not-a-screen.md) ruled out driving a coding
agent through its terminal screen, after five distinct failures and a sixth that
no amount of written guidance could fix. It accepted a real cost for that: print
mode starts the agent fresh every time, so it re-reads the project on every
question and remembers nothing from the last one.

That cost was assumed rather than checked. Claude Code's print mode takes
`--output-format json` and `--resume <session-id>`, and the identifier comes
back in the answer. Asked what a file contained and then "how many characters
was that", it answered both — the second one only makes sense to something that
remembers the first.

Two questions, four and six seconds, each answered with a structured object
carrying the text, the session, the duration and the cost. No terminal, no
dialog, no screen to read.

The same agent also offers `claude mcp serve`, which was worth checking and is
the other direction: it exposes the agent's own tools to a client, rather than
letting a client hold a conversation with the agent.

## Options considered

**Print mode without resuming**, as ADR-VI-020 decided. Correct about the
screen, wrong that the agent must start over.

**Structured streaming both ways**, `--input-format stream-json` with
`--output-format stream-json`, which keeps one process open for a whole
conversation. The most capable option, and the right one the day the bridge
wants partial output while an agent is still working. Rejected for now: it means
owning a long-lived subprocess and its lifecycle, and the gateway already owns
processes.

**A resumable print session.** Accepted.

## Decision

A spoken request reaches a coding agent as `claude -p --output-format json`,
and every request after the first in the same room adds
`--resume <session-id>` with the identifier the previous answer returned. The
identifier is remembered where the rest of the conversation is remembered, in
the gateway's room.

## Consequences

The conversation is a conversation. A follow-up can say "that one" and be
understood, the project is not re-read from nothing each time, and answers come
back in seconds rather than minutes. The answer arrives as data, with what it
cost attached, rather than as pixels to be interpreted.

What gets worse: a session identifier is now a thing that can be lost or
crossed. Lose it and the next question starts over, silently — the agent will
answer, it will just have forgotten. Cross it between rooms and one
conversation's context leaks into another's, which is the kind of failure that
is invisible until it is embarrassing.

It also ties this design to one agent's flags. OpenCode and DeepSeek Harness
have their own, and the shape of "ask, keep the identifier, resume" may not
survive contact with either.

## Related

[ADR-VI-020](ADR-VI-020-print-mode-not-a-screen.md),
[ADR-VI-013](ADR-VI-013-the-room-is-the-memory-scope.md).
