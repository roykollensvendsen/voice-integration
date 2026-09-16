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
  a browser, on the laptop or the phone
    │ microphone            │ screen
    │ WebRTC audio          │
    ▼                       │
        gpt-live-1          │                        the voice plane
                │ tool calls (JSON, over the data channel)
                ▼           │
            voice-bridge  ◄─┘                               the edge
                │ HTTPS + Bearer, X-Hermes-Session-Id
                ▼
      Hermes gateway  /v1/runs  /api/sessions          the control plane
                │ A2A, MCP, subagents, toolsets
                ▼
  Claude Code   OpenCode   DeepSeek Harness              the work plane
```

Everything below the voice plane runs on one laptop, and the phone reaches it
over Tailscale
([ADR-VI-009](../decisions/ADR-VI-009-everything-runs-on-the-laptop.md)). The
client is a page the bridge serves, because `gpt-live-1` is reachable over
WebRTC and nothing else, and a browser has WebRTC and echo cancellation already
([ADR-VI-018](../decisions/ADR-VI-018-the-client-is-a-browser-page.md)).

OpenAI's own guide calls this arrangement *client delegation*: the application
connects "any model, agent harness, or service" and "owns permissions,
confirmations, private function execution, and durable task state". Read against
this page, the agent harness is Hermes, the permissions are
[`permissions.md`](permissions.md), the confirmations are the approval flow, and
the durable task state is a room and its runs.

Both ends carry a microphone. The laptop carries a screen as well, and that is
its only privilege: it is where the detail the voice plane deliberately does not
say aloud is read. Neither device is a second assistant. A run started by voice
on the phone is the same run the laptop is talking to, because both address it
by the same gateway session identifier.

## Two microphones, one room

Two audio clients against one room is not the same problem as two screens, and
it is the newest thing in this specification.

* **Cost is per open session, not per sentence.** A realtime session bills while
  it is connected, whether or not anyone is speaking. Two open sessions is twice
  the idle cost of one, and the idle cost is most of the bill for a person who
  talks to their agents for two minutes an hour.
* **A speaker next to an open microphone is a loop.** The laptop plays the
  reply through the same room the laptop is listening to. Browsers give
  acoustic echo cancellation through `getUserMedia`; a native client has to
  bring its own, and a native client that does not have one is unusable rather
  than merely annoying.
* **Who is live has to be a fact, not a race.** If both clients are live, one
  spoken sentence reaches two sessions and the person hears two answers.

So: **at most one client holds the microphone**, and taking it is a deliberate
gesture on that device — a key on the laptop, a button in the application. The
other drops to the screen and stops listening
([ADR-VI-010](../decisions/ADR-VI-010-one-live-microphone.md)). That also
answers, better than a setting could, the question of when the system is
listening: when somebody said so.

Echo cancellation is the browser's, from `getUserMedia`, and so is noise
suppression. That was the largest single cost in the client and it is now
somebody else's. It comes back the day a phone client is written natively, which
is why that is still deferred.

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

A `gpt-live-1` voice session costs $0.05 a minute, billed per second, and the
backend model and tools are charged separately
([the model page](https://developers.openai.com/api/docs/models/gpt-live-1)).
An hour of open microphone is $3.00. That is a number, not a range: the realtime
models it replaced were billed per audio token and ran anywhere from $0.02 to
$0.46 a minute depending on whether prompt caching was holding.

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

The corollary nobody likes: there is no cheaper model to fall back to
([ADR-VI-017](../decisions/ADR-VI-017-the-voice-model-is-gpt-live-1.md)). The
only lever on the bill is how long the microphone is open, which is why claiming
it is a deliberate act rather than a default
([ADR-VI-010](../decisions/ADR-VI-010-one-live-microphone.md)).

**What the ceiling does not cover.** The audio bill is the one this system can
see. The agents' own cost lands elsewhere: on Claude Code's subscription quota,
and on whatever DeepSeek and OpenCode are configured against. `claude -p` draws
from the same five-hour and weekly caps as the Claude chat; the change that
would have moved automated runs to a metered credit pool at API list rates was
announced for 2026-06-15 and paused, not cancelled. That is a row in
[`decisions/deferred.md`](../decisions/deferred.md) with a trigger, because the
day it unpauses, a ceiling on the audio covers the smaller half of the bill.

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
* The room is also the **memory scope**: `X-Hermes-Session-Key` is set to it, so
  voice and typed sessions in one room share long-term memory and different
  rooms share none
  ([ADR-VI-013](../decisions/ADR-VI-013-the-room-is-the-memory-scope.md)).
* Who is speaking is not known, and deliberately so. The unlocked device is the
  authentication
  ([ADR-VI-011](../decisions/ADR-VI-011-the-device-is-the-identity.md)).

Agent-to-agent discussion — the part of the conversation about letting Claude
Code and DeepSeek argue with each other while OpenCode stays out — is a property
of the room, expressed through Hermes' own A2A and subagent machinery. The voice
surface names the room; it does not implement the discussion.

A discussion has a fixed shape, and the shape is what bounds it: one independent
analysis each, one round of criticism each, one joint conclusion, then it stops
whether or not they agree
([ADR-VI-012](../decisions/ADR-VI-012-an-agent-discussion-has-fixed-phases.md)).
What is not yet built is in [`decisions/deferred.md`](../decisions/deferred.md).

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
* The bridge is the only process reachable by both the audio provider and the
  gateway. It is no longer dependency-free — it serves the page and terminates
  the browser's request — and
  [ADR-VI-018](../decisions/ADR-VI-018-the-client-is-a-browser-page.md) records
  what that gave up.

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
2. **The browser client, on the laptop.** A `gpt-live-1` session established by
   exchanging the page's WebRTC offer for an answer through the bridge, the six
   tool definitions, and one microphone. It is built first because it is where
   the person sits, and because it is the cheapest place to find out whether
   this interaction is worth having at all
   ([ADR-VI-014](../decisions/ADR-VI-014-the-linux-client-is-built-first.md)).
3. **The laptop view.** The same room, subscribed to
   `/v1/runs/{run_id}/events`, showing what the voice plane is deliberately not
   saying.
4. **A phone client that survives a locked screen**, against a tool surface that
   has by then been used in anger rather than only designed. The same page works
   on a phone today, as long as it stays in front.
5. **Rooms with more than one agent**, and then — if voice identity is ever
   answered — with more than one person.

Every step leaves something a person can run. What is deliberately not in this
list, and what would make each worth adding, is
[`decisions/deferred.md`](../decisions/deferred.md).

## What is still unsettled

Five of them, in [`open-questions.md`](open-questions.md), which also records
where each of the six that were answered on 2026-09-16 went. None of the five
blocks step 2; four of them are answered *by* step 2, which is most of the
argument for building it next.
