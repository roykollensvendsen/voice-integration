# The system, specified

*Last checked against its sources: 2026-09-16. Everything below that is a fact
about someone else's software carries a link; everything that is a choice
carries a decision record.*

## What this is, in one sentence

A voice layer thin enough to be cheap, in front of a control plane that already
knows how to run agents, so that a person can direct a swarm of coding agents by
talking to it from a phone or a laptop and stay in charge of what they are
allowed to do.

## What it is not

It is not a new agent. It is not a new orchestrator. It is not a chat client.
Every one of those exists already in the Hermes gateway, and the single worst
outcome for this project is a second, worse copy of them. The bridge owns three
things and nothing else: **the shape of the tool surface a voice model is given,
the translation of a gateway reply into a sentence worth hearing, and the third
and narrowest permission layer.**

## The three planes

| Plane | Who is in it | What it holds | What it must never hold |
|---|---|---|---|
| Voice | the realtime model, the person | the last few turns of speech, six tool definitions | transcripts, plans, repository context |
| Control | the Hermes gateway | sessions, runs, approvals, events, routing, memory | the audio stream |
| Work | Claude Code, OpenCode, DeepSeek Harness, Hermes subagents | repositories, terminals, the expensive thinking | the person's attention |

The rule that follows from the table, and that most of this specification exists
to enforce: **context flows down and identifiers flow up.** The voice plane
learns that run `run_ab12` is waiting on an approval to run `git commit`. It
does not learn the diff.

## The shape

```
  phone                     laptop
    │ WebRTC audio            │ HTTP, the same session
    ▼                         │
 OpenAI Realtime API          │      the voice plane
    │ tool calls (JSON)       │
    ▼                         │
 voice-bridge  ◄──────────────┘             the edge
    │ HTTPS + Bearer, X-Hermes-Session-Id
    ▼
 Hermes gateway  /v1/runs  /api/sessions          the control plane
    │ A2A, MCP, subagents, toolsets
    ▼
 Claude Code   OpenCode   DeepSeek Harness         the work plane
```

The laptop is a second view on one session, never a second assistant. This is
the requirement the person stated first and it is the one that decides the
session model: a run started by voice on the phone is the same run the laptop
is watching, because both address it by the same gateway session identifier.

## Why the gateway is Hermes and not ours

Hermes' `api_server` platform already exposes the exact surface this needs:
runs that return immediately and stream lifecycle events, approvals that can be
resolved out of band, steering into a running agent, interruption, and session
listing, forking and continuation — with an API key, CORS, and per-profile
multiplexing. Building that again would be the largest and least interesting
part of this project. [ADR-VI-001](../decisions/ADR-VI-001-hermes-is-the-control-plane.md)
records the decision and what it costs.

The same source says what Hermes does *not* have. Its own capabilities
endpoint reports `"realtime_voice": false` and `"audio_api": false`, and its
voice support elsewhere is push-to-talk: record, transcribe, answer, speak.
That gap is this repository.

## Why the voice layer is our own client and not the ChatGPT app

The architecture the conversation first reached for was: talk to GPT Live in the
ChatGPT app, let it call Hermes as a connector. Two facts kill it.

1. Custom MCP connectors are behind ChatGPT's Developer Mode, which is available
   on Plus, Pro, Team, Enterprise and Edu — [not on Free](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt).
2. MCP tools are [not available while a voice conversation is running](https://www.usecarly.com/blog/chatgpt-mcp/),
   on any plan.

So the one path that would have cost nothing does not exist, and the second one
would not have worked even after paying for it. The voice layer is therefore a
client we own, speaking to the Realtime API directly, which is also the only
arrangement in which the tool surface is ours to design.
[ADR-VI-002](../decisions/ADR-VI-002-our-own-realtime-client.md) records it.

## What it costs, and the rules that follow

Realtime audio is billed per audio token, not per minute. One minute of the
person speaking is about 600 tokens; one minute of the model speaking is about
1200. On `gpt-realtime-2.1` that is $32 per million tokens in and $64 out; the
mini model is $10 and $20. In practice a working agent runs about $0.06–0.11 a
minute on the full model and $0.02–0.05 on the mini once prompt caching is
holding, and $0.18–0.46 a minute when it is not.
([the rates](https://www.eesel.ai/blog/gpt-realtime-mini-pricing),
[measured sessions](https://hackernoon.com/openai-realtime-api-pricing-in-2026-real-world-data-from-4000-measured-sessions))

Three normative rules fall straight out of those numbers.

1. **The session preamble is fixed and small.** It is the same bytes every
   session so that it caches, and it never grows with the number of agents, the
   number of repositories or the number of open runs. Those are looked up, not
   recited.
2. **A spoken reply is capped.** `voice_bridge.speech.SPOKEN_REPLY_MAX_CHARS`
   is the cap and it is 320 characters, which is one or two sentences and an
   identifier. Output audio is the most expensive token there is and the one a
   listener is least able to skip.
3. **Nothing is read aloud that was not written to be heard.** Agent output,
   diffs, logs and stack traces reach the laptop view. The voice plane gets the
   fact that they exist and the identifier that fetches them.

The corollary nobody likes: the mini model is the default, and the full model is
a deliberate, per-session choice. Three times the price for a layer that is
supposed to be routing and small talk is not a trade this system wants by
default.

## The session model

* A **room** is a Hermes session identifier. It is what the phone and the laptop
  share, and it is what makes a conversation resumable an hour later.
* A **run** is one unit of agent work inside a room, created by `POST /v1/runs`
  and addressed by the `run_id` the gateway returns immediately.
* An **approval** is a question a run is blocked on. It is resolved against the
  run, not against the room, because Hermes deliberately keys approval queues by
  run so that answering one cannot unblock another.
* The person is the only participant with standing to resolve an approval. The
  voice plane is a channel they speak through, not a party with authority.

Agent-to-agent discussion — the part of the conversation about letting Claude
Code and DeepSeek argue with each other while OpenCode stays out — is a property
of the room, expressed through Hermes' own A2A and subagent machinery. The voice
surface names the room; it does not implement the discussion. What is not yet
built is in [`decisions/deferred.md`](../decisions/deferred.md).

## Permissions

Three layers, each strictly narrower than the one below it, described in full in
[`permissions.md`](permissions.md):

1. **Harness-native.** Claude Code's own settings, OpenCode's permissions,
   Hermes' toolsets per session, Hermes' Docker terminal backends.
2. **Gateway policy.** Hermes decides what an agent in a role in a session may
   do, and holds the approval queue. This is the authoritative layer.
3. **Voice capabilities.** Which of the six tools this voice session may call at
   all, and which answers it may give to an approval.

The invariant: **the voice layer can only ever narrow.** It has no mechanism for
widening anything. A voice session cannot grant a standing permission, cannot
add a tool to its own surface, and cannot answer an approval in a way that
outlives the single call being asked about. A channel that routinely mishears
short words is not a channel that should be able to say "always".

## Identity and secrets

* The Hermes API key lives in the bridge process and nowhere else. No browser
  and no phone ever holds it.
* The browser's connection to the Realtime API uses an ephemeral client secret
  minted by the bridge per session, so a leaked one expires rather than
  persists.
* The bridge is the only process that is reachable by both the audio provider
  and the gateway, which is exactly why it is small, dependency-free and worth
  reading in full.

## Conformance

Three facts are written down in both prose and code, and `voicebridge check`
compares each pair on every pull request:

| The fact | In prose | In code |
|---|---|---|
| the voice tools | [`voice-contract.md`](voice-contract.md) | `voice_bridge.contract.VOICE_TOOLS` |
| the gateway endpoints | [`hermes-contract.md`](hermes-contract.md) | the `path` of each tool |
| the rules | `# RULE:` markers | rows in `scripts/mutations.toml` |

The third pair is the one that keeps the evidence honest: a rule added without a
mutation row is a rule no test has ever been proven to catch.

## The order this gets built in

1. **The walking skeleton, which is done.** A voice tool call, planned and sent
   as real HTTP to a real server speaking the gateway's contract, rendered back
   as a sentence, with the permission layer in the path. No audio, no model.
2. **The audio client.** A realtime session against the Realtime API, the six
   tool definitions, ephemeral client secrets, and one microphone.
3. **The laptop view.** The same room, subscribed to `/v1/runs/{run_id}/events`,
   showing what the voice plane is deliberately not saying.
4. **Rooms with more than one agent**, and then with more than one person.

Every step leaves something a person can run. What is deliberately not in this
list, and what would make each worth adding, is
[`decisions/deferred.md`](../decisions/deferred.md).

## What is still unsettled

Eight of them, with what would settle each, in
[`open-questions.md`](open-questions.md). Read that before building step 2.
