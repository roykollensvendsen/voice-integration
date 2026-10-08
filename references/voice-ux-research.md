# Making the voice feel natural: what gpt-live-1, ElevenLabs Agents and the field say

*Researched 2026-10-08 by claude-code/opus-5.5. Every page below was read on
2026-10-08, as raw Markdown where the site offers it (OpenAI and ElevenLabs both
serve `<page>.md`), otherwise as HTML. Quotes are verbatim. Nothing here was
measured; where a claim is a vendor's own number it says so.*

Short names used below:

| Name | URL |
|---|---|
| OAI-Live | https://developers.openai.com/api/docs/guides/live |
| OAI-Sessions | https://developers.openai.com/api/docs/guides/live-conversations |
| OAI-Delegation | https://developers.openai.com/api/docs/guides/live-delegation |
| OAI-Prompting | https://developers.openai.com/api/docs/guides/live-prompting |
| OAI-Migration | https://developers.openai.com/api/docs/guides/live-migration |
| OAI-Controls | https://developers.openai.com/api/docs/guides/voice-server-controls?api=live |
| OAI-Agents | https://developers.openai.com/api/docs/guides/voice-agents |
| OAI-Cost | https://developers.openai.com/api/docs/guides/voice-latency-cost?api=live |
| OAI-WARP | https://developers.openai.com/api/docs/guides/realtime-webrtc-warp |
| OAI-Model | https://developers.openai.com/api/docs/models/gpt-live-1 |
| OAI-Ref | https://developers.openai.com/api/reference/resources/live |
| OAI-RT-VAD | https://developers.openai.com/api/docs/guides/realtime-vad |
| OAI-RT-Prompt | https://developers.openai.com/cookbook/examples/realtime_prompting_guide |
| EL-Flow | https://elevenlabs.io/docs/eleven-agents/customization/conversation-flow |
| EL-AgentAPI | https://elevenlabs.io/docs/api-reference/agents/create |
| EL-ToolAPI | https://elevenlabs.io/docs/api-reference/tools/create |
| EL-ClientTools | https://elevenlabs.io/docs/eleven-agents/customization/tools/client-tools |
| EL-ToolInterrupt | https://elevenlabs.io/docs/eleven-agents/customization/tools/tool-configuration/tool-interruptions |
| EL-Events | https://elevenlabs.io/docs/eleven-agents/customization/events/client-to-server-events |
| EL-CustomLLM | https://elevenlabs.io/docs/eleven-agents/customization/llm/custom-llm |
| EL-Auth | https://elevenlabs.io/docs/eleven-agents/customization/authentication |
| EL-JS | https://elevenlabs.io/docs/eleven-agents/libraries/java-script |
| EL-Token | https://elevenlabs.io/docs/eleven-agents/api-reference/conversations/get-webrtc-token |
| EL-Lang | https://elevenlabs.io/docs/eleven-agents/customization/voice/customization/language |
| EL-LangHelp | https://elevenlabs.io/docs/help-center/product/eleven-agents/which-languages-can-i-use-with-eleven-agents |
| EL-Languages | https://elevenlabs.io/docs/help-center/other/what-languages-do-you-support |
| EL-v4 | https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4 |
| EL-Models | https://elevenlabs.io/docs/overview/models |
| EL-Overview | https://elevenlabs.io/docs/eleven-agents/overview |
| EL-Pricing | https://elevenlabs.io/pricing/agents |
| LK-Turns | https://docs.livekit.io/agents/build/turns |
| LK-Detector | https://docs.livekit.io/agents/build/turns/turn-detector |
| LK-Tuning | https://docs.livekit.io/agents/logic/turns/tuning |
| DG-Flux | https://developers.deepgram.com/docs/flux/configuration |
| Stivers 2009 | Stivers et al., "Universals and cultural variation in turn-taking in conversation", PNAS 106(26), doi:10.1073/pnas.0903616106 (abstract via Europe PMC; the PNAS page returned 403) |

## 1. gpt-live-1

### 1.1 Turn detection and endpointing: there are no knobs

- The session takes exactly six startup fields: `model`, `instructions` (up to
  16,384 tokens), `input` (history), `audio.output.voice`, `delegation`, `store`.
  None is about turn detection. (OAI-Sessions, "Configuration fields")
- `session.update` changes only Responses-delegation settings; "other
  configuration fields are rejected". (OAI-Sessions, "Update a live session")
- The full event list in the API reference has no turn, VAD, speech-started or
  speech-stopped event and no `turn_detection` field. Client events are
  `session.start/close/update`, the three appends, `session.input_audio.append`
  and `mute/unmute`. (OAI-Ref, event names enumerated from the page)
- Contrast: the older Realtime models *do* expose `turn_detection` —
  `server_vad` (`threshold` 0.5, `prefix_padding_ms` 300, `silence_duration_ms`
  500 in the example) and `semantic_vad` with `eagerness`
  `low|medium|high|auto` (auto = medium). (OAI-RT-VAD) None of this applies to
  `gpt-live-1`.
- The only documented lever is the prompt. Optional control "Silence and
  background noise", to be added "only when testing shows a need":
  "Keep listening while the user pauses to think. Do not treat a cough, music,
  or nearby conversation as a new request." (OAI-Prompting, Appendix)
- There is no end-of-turn signal for transcripts either: "Transcript deltas have
  no item ID or event that marks a completed conversational turn, so your
  application decides how to group them." (OAI-Sessions, "Transcript deltas")

### 1.2 Barge-in and backchannels

- The model page's one-line pitch: "natural, expressive voice conversations
  with smooth interruption handling"; it "can listen and speak at the same
  time". (OAI-Model)
- Interruption behaviour is prompted, not configured. The recommended prompt
  template has three fixed headings to keep — `Backchannel policy`,
  `Interruption policy`, `Delegation policy` — with defaults "Use moderate
  backchannels. Acknowledge naturally without competing with the main
  response." and "Stop speaking when the user interrupts. Listen to what they
  say." "'Moderate' is a prompting instruction, not a numerical frequency
  setting." A rule that forbids all overlap "can suppress" backchannels.
  (OAI-Prompting)
- Interrupting speech does not stop work: "Interrupting the spoken conversation
  leaves backend work running." "'Stop talking' asks the assistant to yield;
  'Cancel my booking' asks the backend to take an action."
  (OAI-Delegation "Keep updates accurate and useful"; OAI-Prompting "Interruptions")
- An appended instruction "can interrupt the model's current speech or
  behavior". (OAI-Delegation "Send the right kind of update")
- There is no event marking the end of a spoken response: "GPT-Live has no
  corresponding event … Track playback in your client." (OAI-Migration)

### 1.3 Time to first audio

- OpenAI publishes no latency number for `gpt-live-1`. It tells you what to
  measure: "delegation receipt, backend request start, first useful result …
  result submission, audio arrival, and client playback", median and p95, and
  "Measure acknowledgments such as 'I'm checking' separately from the answer
  the caller needs." (OAI-Agents, "Measure latency")
- Connection setup can be shortened with WARP. In a browser: DTLS 1.3 works in
  Chrome without a trial; SNAP needs an origin trial (Chrome 151–156); SPED has
  no browser trial yet. A pre-negotiated data channel (`negotiated: true`,
  `id: 4`, sent as `transport.dcid` in `POST /v1/live/sessions`) works in
  browsers today and saves round trips on its own. (OAI-WARP)
- Every WebRTC session creation bills 15 s up front, credited against the
  session once it runs. (OAI-Cost) Relevant to ADR-VI-027's reconnect-per-voice.
- Backend latency in client mode is ours: keep connections warm, "Stream useful
  results", "Send each result as soon as you have enough text to understand it
  on its own", and optionally start work from transcript fragments before the
  delegation arrives ("Start a speculative lookup when enough information is
  available"; "Discard outdated results"). (OAI-Delegation "Reduce backend
  latency", "React to transcript fragments")

### 1.4 Keeping a delegated turn natural while the backend is slow

- Multiple appends per delegation are allowed: "You can send multiple updates
  with the same client delegation ID." (OAI-Delegation "Receive a client
  delegation")
- Which event: `thinking.append` = "facts or progress that it can use in later
  replies without saying them when they arrive"; `commentary.append` = results
  "GPT-Live should say aloud; it is trained to paraphrase the text";
  `instructions.append` = "greeting, disclosure, or direction to stop speaking".
  (OAI-Delegation table)
- Cadence: "send an update when something useful changes: a step finishes, a
  delay matters, or the user needs to answer a question. Use
  `session.thinking.append` for background progress in client mode. Use
  `session.commentary.append` when the update is useful to say aloud." The
  example spoken "Still working" line is "I'm checking the available
  appointments." (OAI-Delegation "Keep updates accurate and useful")
- The acknowledgement while waiting is meant to come from the prompt: "You can
  prompt GPT-Live to acknowledge a request while delegated work runs," and the
  template ends "Delegate before giving an answer that depends on backend work.
  Do not guess the result while waiting." (OAI-Prompting "Delegation")
- Have the backend label output as progress vs result so the app can choose the
  event. (OAI-Delegation "Forward complete, useful updates")
- Corrections: track a task revision; when "Friday" becomes "Thursday", "ignore
  results from the outdated Friday request". (OAI-Delegation; OAI-Migration)

### 1.5 Documented limits on appends

- `content` is a plain string, **max 500 tokens per append**; `delegation_id`
  is required (`null` for session-wide); a non-null id "must identify a known
  client delegation". (OAI-Delegation; OAI-Sessions)
- No documented limit on the *number* of appends, and no rate limit for them.
  (Absence noted across OAI-Delegation, OAI-Sessions, OAI-Ref.)
- The acknowledgement "arrives when the session timeline reaches the estimated
  end of the added context" — not speech. "If the session timeline stops, the
  acknowledgment can remain pending." (OAI-Sessions)
- "The assistant may repeat information supplied through any of these events."
  (OAI-Sessions)
- Context: 128k tokens; past 90 % a replacement engine starts inside the session
  with the original instructions and up to 8,192 tokens of history. Startup
  `input` takes up to 128 messages / 8,192 tokens. (OAI-Sessions)
- Rate limit is concurrent sessions (50 on the lowest paid tier). (OAI-Model)

### 1.6 Recovery

- `session.closed.reason`: `close_requested`, `expired`, `content`,
  `remote_hangup`, `connection_lost`. Moderation can either end the session or
  "cut off assistant audio for the remainder of its current speech and emit an
  `error` event without ending the session." (OAI-Sessions)
- Reconnect: fork a stored session (`store: true`, 30-day retention, not under
  ZDR) or seed a new one with text history; either way "check unfinished
  actions with your backend … so late results from the previous session cannot
  overwrite newer work." (OAI-Sessions "Recover from a failed connection")
- Before retrying a failed tool: "check whether the original action already
  happened … If the outcome is unclear, say so and offer the next useful step."
  (OAI-Delegation)

## 2. ElevenLabs Agents (formerly Conversational AI)

### 2.1 How a browser connects

- `@elevenlabs/client` (npm). Voice conversations "use WebRTC" and text-only
  "use WebSocket by default"; `connectionType` can force either. (EL-JS)
- Private agents: the server mints a **conversation token** for WebRTC
  (`GET /v1/convai/conversation/token?agent_id=…`) or a **signed URL** for
  WebSocket (`GET /v1/convai/conversation/get-signed-url`); "The signed URL
  expires after 15 minutes." The API key stays on the server. (EL-Token; EL-Auth)
- In WebRTC mode audio is fixed at PCM 48 kHz. (EL-JS)
- Note for ADR-VI-006/018: this is an npm package, i.e. a page dependency; the
  WebSocket protocol is documented (AsyncAPI) if a hand-written client is
  preferred. (EL-JS; https://elevenlabs.io/docs/eleven-agents/api-reference/eleven-agents/websocket)

### 2.2 How the agent reaches our backend

Three routes, all documented:

| Route | What it is | Fit here |
|---|---|---|
| **Client tool** | A function registered in the page (`clientTools: { name: async (params) => … }`). With "Wait for response" (`expects_response: true`) "the agent will wait for its response and append the response to the conversation context." `response_timeout_secs` default 20, range 1–120, or `-1` "to wait for the client's response indefinitely (requires expects_response)". (EL-ClientTools; EL-ToolAPI) | Best fit: the page already calls `/delegation`; nothing on the laptop is exposed. |
| **Webhook (server) tool** | ElevenLabs' servers call an HTTPS URL; timeout 5–300 s. (EL-ToolAPI) | Needs the bridge reachable from the internet. |
| **Custom LLM** | Point the agent at an OpenAI-compatible `/v1/chat/completions` or `/v1/responses` endpoint streaming SSE; ElevenLabs' own guide uses ngrok to make it public. (EL-CustomLLM) | The bridge *becomes* the agent's brain (closest to client delegation), but must be public. |

Other relevant tool settings (EL-ToolAPI):
- `execution_mode`: `immediate` (default), `post_tool_speech` ("waits for the
  agent to finish speaking before executing"), `async` ("runs the tool in the
  background without blocking - best for long-running operations"). How an
  async result is later voiced is not described on the pages read.
- `pre_tool_speech`: `auto` ("decides based on recent tool latency"), `force`,
  `off` — the agent says something before the call.
- `tool_call_sound`: `typing`, `elevator1–4`; plays during execution.
- `interruption_mode` per tool: `allow` (default), `disable_during_tool`,
  `disable_during_tool_and_turn`. (EL-ToolInterrupt)

Pushing news in later (EL-Events; EL-JS):
- `contextual_update` / `sendContextualUpdate(text)`: "non-interrupting
  background information" — the equivalent of `thinking.append`.
- `user_message` / `sendUserMessage(text)`: treated as if the user said it and
  "will prompt the agent to take its turn" — the only documented way to make
  the agent speak unprompted; there is no `commentary.append` equivalent.
- `user_activity`: resets the turn timeout.

Custom-LLM "buffer words": for slow backends, stream a first chunk ending in
`"... "` (ellipsis plus space) so TTS keeps natural prosody while the rest is
generated. (EL-CustomLLM "Optimizing for slow processing LLMs")

### 2.3 Turn-taking and interruption settings

All under `conversation_config.turn` (EL-AgentAPI; EL-Flow):

| Field | Default | Range / values |
|---|---|---|
| `turn_model` | `turn_v3` | "Version of the turn detection model" |
| `turn_eagerness` | `normal` | `patient`, `normal`, `eager` |
| `speculative_turn` | `false` | "starts generating LLM responses during silence before full turn confidence is reached … May increase LLM costs." |
| `spelling_patience` | `auto` | waits longer while spelling numbers and names |
| `turn_timeout` | 7 s | 1–30 s ("Take turn after silence": re-engage the user) |
| `silence_end_call_timeout` | −1 (off) | |
| `soft_timeout_config.timeout_seconds` | −1 (off) | 0.5–8.0 s, recommended 3.0 |
| `soft_timeout_config.message` | "Hhmmmm...yeah." | 1–200 chars |
| `use_llm_generated_message` | false | a light LLM writes a contextual filler from the last 4 messages |
| `additional_soft_timeout_messages`, `randomize_fillers`, `max_soft_timeouts_per_generation` (default 1) | | several varied fillers per wait |
| `conversation.max_duration_seconds` | 600 | 60–7,200 |

- Interruptions are on by default and switched as a client event in the
  dashboard. (EL-Flow)
- ElevenLabs' advice on fillers: "Avoid time indicators in filler messages
  (e.g., 'One second...') as actual response times are unpredictable." (EL-Flow)
- The platform includes "A proprietary turn-taking model that handles
  conversation timing". (EL-Overview) No language list for the turn model was
  found; whether it is tuned for Norwegian is **unknown**.

### 2.4 Norwegian and voice quality

- Norwegian is listed for Eleven v3 (74 languages), Flash v2.5 (32 languages)
  and Eleven v4 ("Norwegian Bokmål"). Multilingual v2's 29 does not need
  checking here. (EL-Languages; EL-v4)
- Which model agents default to is inconsistent across the docs: the help page
  says "New agents use Eleven v4 Turbo by default" (EL-LangHelp); the language
  guide says new agents get "Flash v2 model for fast, English-only responses"
  and that adding languages switches to "v2.5 Multilingual" (EL-Lang). Check in
  the dashboard.
- Vendor latency claims (model inference only, marked † on the page): Flash
  v2.5 ~75 ms, Eleven v4 Turbo ~100 ms median, `eleven_v3_conversational`
  ~280 ms. (EL-Models; EL-Languages) No end-to-end agent latency figure was
  found.
- Eleven v4 deliberately drops a cloned voice's native accent in other
  languages; "test this behavior directly". (EL-v4) Relevant if Roy clones his
  own or a Norwegian voice.

### 2.5 Pricing against a normal subscription

From EL-Pricing (the page's own FAQ text):
- "ElevenAgents plans are billed by call minutes, not by the shared credit
  pool." Included minutes / concurrent calls: Free 15/4, Starter ($6) 75/6,
  Creator ($22) 275/10, Pro ($99) 1,238/20, Scale ($299) 3,738/30, Business
  ($990) 12,375/40.
- Extra minutes $0.08; burst above the concurrency limit $0.16.
- "LLM usage is billed separately on top, based on the model you choose" and is
  "deducted from your ElevenLabs credits"; the minute estimates assume the
  platform's LLMs, and a custom LLM is billed by its own provider.
- A "silence discount" exists: `retranscribe_on_turn_timeout` "Disables silence
  discount billing" (EL-AgentAPI). Its size is not stated on the pages read.
- Compare: gpt-live-1 is $0.05/min flat, voice only. (OAI-Model)

## 3. General practice that applies to speech-to-speech plus a slow backend

- **Humans leave short gaps.** Across 10 languages, conversation shows "a
  general avoidance of overlapping talk and a minimization of silence between
  conversational turns", with language means "within a range of 250 ms from
  the cross-language mean". (Stivers 2009) A 5–15 s backend can never be
  hidden; it can only be *acknowledged* quickly.
- **Endpointing numbers in current stacks.** LiveKit: wait 0.5–3.0 s after
  speech (0.3–2.5 s with its audio turn detector), optional `dynamic` mode that
  adapts within that range from the session's own pause statistics. (LK-Turns;
  LK-Detector) OpenAI Realtime server VAD example: 500 ms silence. (OAI-RT-VAD)
  Deepgram Flux: `eot_threshold` 0.7 default, `eot_timeout_ms` 5,000 default.
  (DG-Flux) A semantic or model-based detector waits longer when the words
  trail off ("I need to think about that for a moment"). (LK-Detector; OAI-RT-VAD)
- **Eager start, cheap abort.** Flux fires `EagerEndOfTurn` at a lower
  threshold (suggested 0.4) and `TurnResumed` if speech continues, cancelling
  the speculative work; the final transcript "will exactly match" the eager one.
  (DG-Flux) LiveKit enables preemptive generation by default, skips it for
  utterances over 10 s ("Long turns are more likely to mutate"), max 3 retries.
  (LK-Tuning) ElevenLabs: `speculative_turn`. OpenAI: speculative lookups from
  transcript fragments, discard outdated results. (OAI-Delegation)
- **False barge-in.** LiveKit separates real interruptions from backchannels
  ("adaptive" mode) and, if an interruption yields no words, resumes speaking
  after `false_interruption_timeout` (2 s in its example). (LK-Turns)
- **Acknowledge, then deliver.** Speak a short preamble at the moment the work
  is handed off ("Before any tool call, say one short line like 'I'm checking
  that now.'"). (OAI-RT-Prompt) Fill only when the wait is real: ElevenLabs'
  soft timeout fires only if the answer is later than the threshold (3 s
  recommended) and "only once per turn" by default. (EL-Flow) Measure the
  acknowledgement and the answer separately. (OAI-Agents)
- **Avoid repetition.** Models copy sample phrases: "it may overuse them,
  making responses sound robotic or repetitive"; the fix shown is a `Variety`
  rule ("Do not repeat the same sentence twice. Vary your responses…").
  (OAI-RT-Prompt) ElevenLabs offers several filler messages, shuffled, or
  LLM-generated ones. (EL-AgentAPI) gpt-live "may repeat information supplied
  through any of these events" (OAI-Sessions), so send each fact once.
- **Recovery paths.** Say what is known ("If the outcome is unclear, say so and
  offer the next useful step"), never re-run an action without checking it did
  not happen, version tasks so stale results are dropped. (OAI-Delegation)

## What this means for us

Ordered by expected gain for effort. "Config" means the session prompt or
constants in `live.py`; "page" means `client/index.html`; "bridge" means the
Python server.

1. **Rewrite the session prompt in the vendor's shape (config change).** Our
   five-sentence `INSTRUCTIONS` lack the three headings OpenAI says to keep.
   Add, in Norwegian: a `Backchannel policy` (moderate), an `Interruption policy`
   (stop and listen; "stopp" is yielding, "avbryt" is a backend action), a
   `Delegation policy` ending "Delegate before giving an answer that depends on
   backend work. Do not guess the result while waiting.", the optional
   *silence* line ("keep listening while the user pauses to think") for the
   split-turn problem, and a `Variety` rule. This is the only endpointing lever
   gpt-live has; there is no VAD setting to tune.
2. **Acknowledge from the prompt, progress as thinking, news as commentary
   (config + page change).** Tell the voice in the prompt to say one short,
   varied line whenever it delegates — that is immediate, where our 600 ms
   holding `thinking.append` arrives after the moment has passed. Keep the
   timer, but use it for facts ("Claude Code is running the tests; nothing is
   finished yet") rather than "say you are on it". For long runs, forward
   step completions from `/run` as `thinking.append` and send a spoken
   `commentary.append` only when something matters (a step finished after
   ~20 s, a question, a failure). Never put a time promise in a filler.
3. **Measure the stages before tuning (page change).** ADR-VI-031 traces turns;
   add the stages OpenAI names — delegation received, bridge answered, append
   acknowledged, first output transcript after it — and report median and p95.
   Without these, changes 1, 2 and 5 cannot be compared.
4. **Treat a correction or "avbryt" as a task change, not just a barge-in
   (page + bridge change).** Give each delegation a revision; when the user
   corrects or cancels while a run is going, drop the stale result instead of
   speaking it, and tell the backend to stop. Interrupting the voice does not
   stop Hermes or a Claude Code session today.
5. **Pre-negotiate the data channel and send `transport.dcid` (page + bridge
   change).** Works in browsers now (WARP's channel part plus DTLS 1.3 in
   Chrome) and shortens every session start — which ADR-VI-027 makes happen on
   every change of voice. Each start also bills 15 s up front.
6. **Say failures plainly and route them (bridge change).** Turn bridge
   errors, `session.closed` reasons and moderation cut-offs into one short
   spoken sentence plus the next step, and reconnect with seeded history
   instead of "The bridge did not answer: <exception>". Check whether a run
   already happened before any retry.
7. **ElevenLabs as an optional engine behind a toggle (new engine).** Build it
   as a second page module, chosen at "Take the microphone", with gpt-live the
   default and its code path untouched. Use a **client tool** (`ask_backend`,
   `expects_response: true`, `response_timeout_secs: -1` or 120) that calls the
   same `/delegation`, so nothing on the laptop is exposed and ADR-VI-003's
   narrowing still applies. Configure `turn_eagerness: patient`, soft timeout
   3 s with several shuffled Norwegian fillers, `pre_tool_speech: force`, and
   `sendContextualUpdate` for progress. Mint the WebRTC conversation token in
   the bridge. Open questions to settle by trying it: Norwegian quality of the
   turn model, how to speak a result that arrives minutes later (only
   `sendUserMessage` triggers a turn), and whose LLM chooses when to call the
   tool (an ElevenLabs-hosted LLM bills credits; a custom LLM endpoint would
   need the bridge public). Cost: plan minutes, then $0.08/min plus LLM, against
   gpt-live's flat $0.05/min.
8. **Eager start from transcript fragments, later (page + bridge change).**
   Once 3 shows where time goes: start cheap read-only work (status, recap)
   from transcript fragments before the delegation arrives, and discard it if
   the turn changes. Not for anything that acts on the machine.
