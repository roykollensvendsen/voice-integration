# ADR-VI-002: The voice layer is our own Realtime client, not the ChatGPT app

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

The stated requirement was to keep using GPT Live, from a phone and from a
laptop, because it is the best voice interface the person has used. The obvious
reading is: keep the ChatGPT app, and let it reach the gateway through a
connector.

Two facts, checked on 2026-09-16, close that path.

1. Custom MCP connectors live behind ChatGPT's Developer Mode, available on
   Plus, Pro, Team, Enterprise and Edu, and [not on Free](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt).
   The account in question is Free.
2. MCP tools are [not available while a voice conversation is running](https://www.usecarly.com/blog/chatgpt-mcp/),
   on any plan. Paying would not have opened the path either.

The underlying model is available directly: OpenAI's Realtime API serves the
same family, including a mini variant priced at $10 and $20 per million audio
tokens in and out against the full model's $32 and $64.

## Options considered

**Wait for ChatGPT voice to gain tool calling.** Costs nothing and might happen.
Rejected as a plan, kept as a trigger: it is a row in `deferred.md`, because the
day it lands this decision is worth revisiting.

**A bridge that drives the ChatGPT app.** Automation against an interface not
meant to be automated, breaking on any change, and against the spirit of the
terms. Rejected.

**Hermes' own voice mode.** It exists, and it is push-to-talk: record,
transcribe, answer, speak. Hermes' own capabilities endpoint reports
`"realtime_voice": false`. It is not full duplex and it is not what was asked
for. Rejected as the primary interface; kept as the fallback if question 1 in
`open-questions.md` is answered "no budget".

**Our own Realtime client.** Accepted.

## Decision

The voice layer is a client this project owns, speaking to the OpenAI Realtime
API, configured with the six tools in `docs/voice-contract.md`.

## Consequences

The tool surface becomes ours to design, which is the whole reason the token
rules in `docs/specification.md` are enforceable at all. Running from phone and
laptop becomes a question of where the client is served rather than what the app
supports.

What gets worse: the app's polish is gone. No chat history, no ChatGPT memory,
no share sheet, no app-level integrations — and a real bill where there was
none. If the actual requirement turns out to be the app rather than the
interaction, this decision is wrong, which is why question 2 in
`open-questions.md` asks it directly and asks for ten minutes of evidence rather
than an opinion.

## Related

[`docs/specification.md`](../docs/specification.md),
[`docs/open-questions.md`](../docs/open-questions.md).
