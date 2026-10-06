# The claude-voice contract

What this bridge asks of [claude-voice](https://github.com/roykollensvendsen/claude-voice),
the MCP server on the same laptop that runs and watches Claude Code sessions,
and what it deliberately leaves alone. Why it asks anything at all is
[ADR-VI-024](../decisions/ADR-VI-024-coding-sessions-are-heard-from-claude-voice.md).

claude-voice speaks MCP over Streamable HTTP at `http://127.0.0.1:8811/mcp`.
`VOICE_BRIDGE_CLAUDE_VOICE` overrides that address. The bridge sends the local
static token as `Authorization: Bearer`. It takes the token from
`CLAUDE_VOICE_TOKEN` in its own environment if set, and otherwise from that
line in `~/.config/claude-voice/env`. Without a token the bridge does not try at
all, and nothing else changes.

## What we call

<!-- normative: claude-voice tools -->

| Tool | Why we call it | Answered with |
|---|---|---|
| `whats_new` | every six seconds, for what happened since the last cursor | `cursor`, and `events` each with `session`, `kind`, `text`, `ts` |
| `approve` | a plain yes, or the button, for one request that is waiting | the request that was settled |
| `deny` | a plain no, or the button, for the same | the request that was settled |

`voice_bridge.sessions.TOOLS` holds the same three, and the client refuses any
other name before anything is sent. `voicebridge check` fails when this table
and that tuple disagree.

## How a call travels

1. `initialize`, once. The answer's `Mcp-Session-Id` header is kept and sent on
   every later request.
2. `notifications/initialized`, once, with no answer expected.
3. One `tools/call` per call. The reply may be plain JSON or a server-sent
   event stream; in the second case the `data:` line carrying the reply is read.
   The result is in `result.structuredContent`. A result marked `isError` is a
   refusal and is said as one.

If the session has expired, the server answers `404`. The bridge opens a new
session and tries once more.

## What is read aloud

The first `whats_new` has no cursor and only sets the starting point, so old
news is never read out. After that, every event goes onto the watch stream as
`claude.news`, with the sentence claude-voice wrote. The page says aloud the
kinds in `voice_bridge.sessions.SPOKEN` — a session that finished, failed,
needs input or wants permission — and only shows the rest.

An approval number is not read aloud. claude-voice ends a request with
"Approval 3: yes or no?", and the bridge removes the number before anything
hears it; a person answers the question they just heard, not a number.

## What we do not call, on purpose

The other seventeen tools stay with the gateway, if anything. Starting a
session, sending one a message, reading what it wrote: each of those is a
request that needs planning, and planning is the gateway's
([ADR-VI-001](../decisions/ADR-VI-001-hermes-is-the-control-plane.md)).
`list_pending_approvals` is not needed, because every request arrives as news.
