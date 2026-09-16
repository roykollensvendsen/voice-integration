# What is still unsettled

Eleven questions. Each one has an answer that changes what gets built, and none of
them is answered by building more of what is already here. The column that
matters is the last one: what would settle it.

| # | The question | Why it is not a detail | What would settle it |
|---|---|---|---|
| 1 | Who pays for the audio, and up to what ceiling? | Free ChatGPT is not API access. The Realtime API bills per audio token from a funded OpenAI account, and an always-listening session bills while nothing is happening | A funded account, a chosen model (`mini` or full), and a monthly ceiling written into the config |
| 2 | Is the requirement "a voice interface this good", or "the ChatGPT app specifically"? | Our own Realtime client gets the same model and none of the app's polish — no chat history, no memory, no phone integration. If the second is the real requirement, this design is wrong | Ten minutes with a bare Realtime client, answering whether it is good enough |
| 3 | Where does the bridge run, and how does the phone reach it? | The phone needs a reachable endpoint. A laptop behind a home router is not one. Every answer — Tailscale, Cloudflare tunnel, VPS — changes the threat model and the TLS story | A chosen network path, and an ADR recording what it exposes |
| 4 | Where do the agents' tools actually execute? | Hermes' API server reports `"tool_execution": "server"` and `"split_runtime": false`: tools run on the gateway's host. Agents working on your repositories means Hermes running where your repositories are, which collides with question 3 | A decision on gateway placement: your laptop reachable from outside, or a VPS with the repositories on it |
| 5 | Can Claude Code be driven by a gateway under your existing subscription, or does the adapter need the Anthropic API? | It is the difference between "already paid for" and a second metered bill, and it is a terms question as much as a technical one | Reading Anthropic's terms for non-interactive use, and one working adapter either way |
| 6 | Who is allowed to speak? | The bridge knows a voice session, not a person. Anyone within earshot of an unlocked phone can answer an approval. `deny`-only is a mitigation, not an answer | A decision on voice identity: a wake phrase is not authentication, a locked device might be |
| 7 | What happens to audio that was never meant for the system? | Full duplex means the microphone is open. In a house with other people, that is a recording decision, not a feature flag | A stated policy on when the session is open, and a visible indicator when it is |
| 8 | When agents discuss, what stops them? | Two agents arguing is two token streams with no natural end. The conversation asked for this explicitly; nothing in it bounds the cost | A turn limit, a token budget, or a person in the loop — chosen before the feature, not after the bill |
| 9 | Do voice sessions share a memory scope with typed ones? | Hermes scopes long-term memory by `X-Hermes-Session-Key`. Sharing gives continuity across phone and laptop; it also means anything said aloud is remembered by everything else | A decision on the session-key scheme, and a test that shows what crosses |
| 10 | When both microphones are open, which one is live? | Two live sessions means one sentence answered twice, and two idle sessions billed. Handing the microphone over has to be an act, not a race | A chosen handover: last speaker wins, an explicit claim, or push-to-talk on the laptop |
| 11 | One client in a browser, or a native one per device? | A browser is one implementation for both ends and gets echo cancellation free from `getUserMedia`; native gets a hotkey and survives the browser being closed. The laptop's speaker sits next to the laptop's microphone either way | A decision, and an ADR: it also decides whether the bridge has to serve static files |

## How to read this page

These are not risks to be noted and moved past. Questions 1, 3 and 4 together
decide whether the system can exist in the form described; 5 decides how much it
costs to run; 6 and 7 decide whether it should be left switched on; 10 and 11
decide what the client actually is. Steps 2 and later in
[`specification.md`](specification.md) should not start until 1 to 4 and 11 have
answers.

A question that gets answered moves out of this table and into a decision record
under [`decisions/`](../decisions/README.md), with the answer and what it cost.
