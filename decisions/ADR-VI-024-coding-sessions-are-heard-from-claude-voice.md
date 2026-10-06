# ADR-VI-024: Coding sessions are heard from claude-voice, and answered there

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-06. A second hole in
[ADR-VI-001](ADR-VI-001-hermes-is-the-control-plane.md), next to
[ADR-VI-022](ADR-VI-022-a-short-path-past-the-control-plane.md).

## Context

Most of the Claude Code work on this machine does not start from the voice. It
starts in a terminal, or from the phone through
[claude-voice](https://github.com/roykollensvendsen/claude-voice), an MCP server
on the same laptop that runs and watches Claude Code sessions. When one of those
sessions finishes, fails or stops to ask for permission, the person finds out
only by looking at a screen. Walking with the microphone open, they hear nothing.

claude-voice already keeps that news. Its `whats_new` tool returns what has
happened since a cursor, one sentence per event, written to be read aloud. Its
`approve` and `deny` tools answer one waiting request by its number, and a number
works once. A request nobody answers is refused after ten minutes.

The gateway could reach all of this as an MCP client. But to hear news promptly,
somebody has to ask every few seconds. Through the gateway, every one of those
asks is a planning turn on a per-token model, carrying thirty-three thousand
tokens of preamble.

## Options considered

**Ask through the gateway.** Add claude-voice to Hermes' MCP servers and let it
poll. No code here. Rejected for news and approvals: polling every six seconds
would make the gateway the most expensive part of the system while saying
nothing most of the time. It also puts a language model between the person's
"yes" and the approval, which [ADR-VI-003](ADR-VI-003-the-voice-layer-can-only-narrow.md)
exists to prevent. It is still the right path for open requests such as "tell
the build session to rerun the tests", and that is a separate change.

**Leave it.** The person keeps looking at a screen. Rejected: it is the reason
the voice exists.

**The bridge asks claude-voice directly, for news and answers only.** Accepted.

## Decision

The bridge polls claude-voice's `whats_new` while it runs, at
`http://127.0.0.1:8811/mcp`, using the local static token from
`~/.config/claude-voice/env`. Each event goes onto the watch stream. The page
reads a session that finished, failed, needs input or wants permission aloud,
and only shows the rest. A request for permission is remembered, and a plain yes
or no, or a button, answers it with `approve` or `deny`. The bridge may call
those three tools and no others.

## Consequences

News from every Claude Code session on the machine is heard within a few
seconds, and answering costs no model call at all.

A permission answered this way is one tool call, once. A number claude-voice
hands out is used up when it is answered, so "always" cannot be expressed,
however the person phrases it.

What gets worse: the bridge now holds a third secret, and it talks to a second
backend that has its own idea of what a session is. If claude-voice is not
running, the bridge says so once on the screen and keeps trying, quietly.

The voice may also become chatty. Every terminal session that finishes a turn is
news, and a busy afternoon will produce a lot of it. Which kinds of news are read
aloud is one tuple in `voice_bridge.sessions`, so it is cheap to narrow.

## Related

[`docs/claude-voice-contract.md`](../docs/claude-voice-contract.md),
[`docs/permissions.md`](../docs/permissions.md),
[ADR-VI-004](ADR-VI-004-identifiers-up-context-down.md).
