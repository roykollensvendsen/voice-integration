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
| `list_active_sessions` | the tree on the page, and matching a spoken name | `sessions`, each with `name`, `project`, `status`, `kind` |
| `ask_active_session` | a turn while one session is the target | `status`, `reply`, `next_after`, `session_ended` |
| `read_session_output` | the rest of an answer that outlasted the wait | `turns` after a given index, and `next_after` |
| `session_tree` | the tree on the page: subagents, and who has messaged whom | `version`, and `nodes` with `id`, `name`, `kind`, `parent_id`, `talks_to` |
| `fleet_recap` | "what are the sessions doing", and a line under each session in the tree | `sessions`, each with `name`, `status` and `doing`, one line saying what it is doing |
| `digest_session` | "oppsummer" a session: its long conversation summed up outside anybody's context, in the voice's language | `digest`, at most about 600 characters, and how much was considered |
| `cancel` | "avbryt": stop the current turn of a session claude-voice runs; a terminal session answers that only its screen can stop it | `status`: `interrupted`, `not_running` or `not_supported` |
| `start_active_session` | "start en ny økt i …": a Claude Code session started in the background in that project, and chosen at once | `name`, `claude_session_id`, `project`, `status`, once it is among the running sessions |
| `stop_active_session` | "lukk denne økta": stop a session `start_active_session` started; claude-voice refuses any other | `name`, and `status`: `stopped`, `not_started_here` or `not_running` |
| `health` | claude-voice's half of the health summary the page and the voice read | `now`, `tools` with latency and errors, the latest `errors`, `courier`, `watcher` |

`voice_bridge.sessions.TOOLS` holds the same thirteen, and the client refuses any
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

## Nothing heard is lost

The bridge keeps its place in the news, the news worth saying aloud, and how
far the person has heard it, in `news.json` beside the target in its state
directory, so a restart picks up where it left off
([ADR-VI-029](../decisions/ADR-VI-029-the-bridge-owns-every-open-request.md)).
The page reports each piece of news it says with `POST /heard`. When a session
opens, `POST /session` answers with `missed`: what was worth saying and not yet
heard, the latest `MISSED_SPOKEN` of it word for word and the rest counted. The
page says that first, as "while you were away".

An answer from the gateway that no page is waiting for, because nobody has asked
after the run for `UNWATCHED_SECONDS`, is told as news in the same way.

## Talking to one session

While one session is the target
([ADR-VI-026](../decisions/ADR-VI-026-you-choose-who-you-talk-to.md)), each
turn is `ask_active_session` with the words as they were said, waiting up to
`ASK_SECONDS`. claude-voice answers with one of four states:

* `answered`: the reply is spoken.
* `needs_input`: the session waits for somebody at its own screen. That is said,
  and the target stays.
* `session_ended`: the target goes back to the voice, and that is said.
* `still_working`: nothing it wrote is quoted. The voice says once that the
  session is busy, and the bridge waits in the background. It asks
  `read_session_output` for turns after `next_after` every few seconds, and
  looks for the turn that carries what was said. The answer is the last thing
  the session wrote after that turn, and before the next thing it was asked.
  It is told as news once the next turn has begun or the session is idle.
  Anything written before the question reached it, for other people or other
  prompts, is never the answer.

The tree on the page is `session_tree`, fetched again whenever `whats_new`
reports `tree_changed`, which is never spoken. A node can be chosen when
`list_active_sessions` names it; a subagent or a session the bridge runs
itself is shown but cannot be chosen yet. `talks_to` is drawn as the names a
session has sent messages to in the last day.

* `needs_choice`: the session has a choice box open, and nothing reaches it
  until somebody answers at its keyboard. The question and its choices are
  said, with the advice to answer at the screen.

While a session is the target, a hook in the person's Claude Code settings
refuses choice boxes in that session, so it asks in its reply instead
([ADR-VI-030](../decisions/ADR-VI-030-no-choice-box-in-a-session-spoken-to.md)).
The bridge therefore keeps the session's `claude_session_id` in `target.json`.

## What we do not call, on purpose

The other nine tools stay with the gateway, if anything. Starting a
session, sending one a task, summarising a fleet: each of those is a request
that needs planning, and planning is the gateway's
([ADR-VI-001](../decisions/ADR-VI-001-hermes-is-the-control-plane.md)).
`list_pending_approvals` is not needed, because every request arrives as news.
