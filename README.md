# voice-integration

Talk to your coding agents. From the phone, from the laptop, in the same
session, without handing a microphone the keys to your repositories.

A thin voice layer in front of the [Hermes Agent](https://github.com/NousResearch/hermes-agent)
gateway, which already knows how to run Claude Code, OpenCode, DeepSeek Harness
and its own subagents, hold their sessions, stream their events and stop them to
ask you a question. This repository builds the edge: the six tools a realtime
voice model is given, the translation of a gateway reply into a sentence worth
hearing, and the permission layer that can only ever narrow.

```
  phone                laptop
    │ microphone         │ microphone        │ screen
    ▼                    ▼                   │
      OpenAI Realtime API                    │     the voice plane
                │ tool calls (JSON)          │
                ▼                            │
            voice-bridge  ◄──────────────────┘            the edge
                │ HTTPS + Bearer
                ▼
      Hermes gateway  /v1/runs  /api/sessions         the control plane
                │ A2A, MCP, subagents, toolsets
                ▼
  Claude Code   OpenCode   DeepSeek Harness             the work plane
```

The client is a page. `gpt-live-1` is reachable over WebRTC and nothing else,
and a browser brings WebRTC, echo cancellation and noise suppression with it.
Everything below the voice plane runs on one laptop, reached from the phone over
Tailscale. At most one page holds the microphone at a time, and taking it is a
deliberate act.

**Context flows down, identifiers flow up.** The voice plane learns that
`run_ab12` is waiting on an approval. It never learns the diff.

## Start here: talking to it on one computer

You need Linux or macOS, an [OpenAI API key](https://platform.openai.com/api-keys)
and a browser. The voice is OpenAI's, billed by the minute while the microphone
is open; the bridge refuses to go past a monthly ceiling, twenty dollars unless
you set another. An assistant doing this for you should read
[AGENTS.md](AGENTS.md) first.

<!-- not run: installs software on the reader's computer; the clean-install job runs it in an empty container on every change -->
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv, which installs Python tools
export PATH="$HOME/.local/bin:$PATH"
uv tool install git+https://github.com/roykollensvendsen/voice-integration
voicebridge ready
```

`ready` lists what is still missing, and what to do about each. On a computer
with no key yet (the empty `OPENAI_API_KEY=` stands in for one), it says:

```console
$ OPENAI_API_KEY= voicebridge ready --offline
missing  openai_key    no OpenAI API key, so no voice session can be opened
                       fix: put OPENAI_API_KEY=<your key> in ~/.config/voice-bridge/env; keys are made at platform.openai.com/api-keys
ok       budget        this month's ceiling is not spent
optional hermes        the planner was not asked (--offline)
optional claude_voice  claude-voice was not asked (--offline)
not ready: openai_key
```

Put the key in that file, readable only by you, and check again:

<!-- not run: writes the reader's own key, which only they have -->
```bash
mkdir -p ~/.config/voice-bridge && chmod 700 ~/.config/voice-bridge
printf 'OPENAI_API_KEY=%s\n' "<your key>" > ~/.config/voice-bridge/env
chmod 600 ~/.config/voice-bridge/env
voicebridge ready                                         # ends with "ready to talk"
voicebridge serve
```

Open `http://127.0.0.1:8760` in a browser on the same computer, press **Take the
microphone**, and talk. That is the voice alone. Two more programs each add
somebody to talk to, and `ready` says whether it can reach them:

* [claude-voice](https://github.com/roykollensvendsen/claude-voice) lets you
  pick a Claude Code session on the computer and talk to it;
* the [Hermes Agent](https://github.com/NousResearch/hermes-agent) gateway is a
  planner that starts and follows work for you.

### From the phone

A browser only lends a page the microphone over HTTPS. With
[Tailscale](https://tailscale.com) on both the computer and the phone, this
gives the page an HTTPS address that only your own devices can reach:

<!-- not run: changes the reader's network; ask before doing it for someone -->
```bash
tailscale serve --bg --https=10000 http://127.0.0.1:8760
```

Open `https://<the computer's name>.<your tailnet>.ts.net:10000` on the phone. On Android, [the phone app](android/README.md) shows the same page and keeps
it going with the screen locked.
If the phone cannot find that name, it is asking ordinary DNS instead of
Tailscale's: turn on **Use Tailscale DNS** in the Tailscale app, and on Android
turn **Private DNS** off.

## The surface

Six tools, fixed, because a realtime session is billed for its own instructions
and a model picking between six well-named things is more reliable than one
picking between thirty:

```console
$ voicebridge tools --names
agent_task
approval_resolve
run_status
run_steer
run_stop
session_recall
```

What a call becomes, before any of it leaves the machine:

```console
$ voicebridge dispatch --dry-run agent_task '{"agent": "claude-code", "instruction": "run the tests", "room": "evening"}'
POST http://localhost:8642/v1/runs
{"input": "run the tests", "model": "claude-code", "session_id": "evening"}
```

And what the voice layer will not do, however nicely you ask it:

```console
$ voicebridge dispatch --dry-run approval_resolve '{"run_id": "run_ab12", "choice": "always"}'
refused: 'always' would outlive this call; voice may answer deny or once
```

Standing permissions are not granted by a channel that is used while walking and
mishears short words. [Why that is a rule](decisions/ADR-VI-003-the-voice-layer-can-only-narrow.md),
not a preference.

## Reading it

| Start here | For |
|---|---|
| [`docs/specification.md`](docs/specification.md) | the system, and the rules the cost of audio forces on it |
| [`docs/open-questions.md`](docs/open-questions.md) | the four things still unsettled, and where the answered ones went |
| [`docs/voice-contract.md`](docs/voice-contract.md) | the six tools, and what the model is told |
| [`docs/hermes-contract.md`](docs/hermes-contract.md) | what we call on the gateway, and what we deliberately do not |
| [`docs/permissions.md`](docs/permissions.md) | three layers, and the invariant that makes them worth having |
| [`decisions/`](decisions/README.md) | why it is this and not something else |

## Talking to it

Once `voicebridge ready` says so:

```console
$ voicebridge serve --help
usage: voicebridge serve [-h] [--host HOST] [--port PORT] [--gateway GATEWAY]

options:
  -h, --help         show this help message and exit
  --host HOST        what to listen on
  --port PORT        what port to listen on
  --gateway GATEWAY  the Hermes gateway
```

Open the address it prints, press **Take the microphone**, and talk. Nothing is
listening before that, and the page holds no key: it makes a WebRTC offer, the
bridge exchanges it for an answer, and the audio goes straight to OpenAI.

Under the conversation is **Underneath**: which tool each agent started, and the
answer as it is written. That is where the detail the voice deliberately does
not read out goes.

## What it costs

Voice is the only part billed by the second, and it bills while the microphone
is open whether or not anyone is speaking. The ceiling is enforced, not noted:

```console
$ voicebridge budget --ledger /dev/null
$20.00 left of $20.00 this month — 400 minutes
```

Twenty dollars is 400 minutes, or about thirteen minutes a day. `--ledger` names
where the spend is kept; without it, this installation's own.

## Running the checks

Every fact stated twice here is compared by something that can fail, and every
rule has to have a test that names it:

```console
$ voicebridge check .
voice tools: 6 in docs/voice-contract.md, 6 in the code, agreed
gateway paths: 7 in docs/hermes-contract.md, 7 in the code, agreed
claude-voice tools: 13 in docs/claude-voice-contract.md, 13 in the code, agreed
rules: 50 in the source, 50 in scripts/mutations.toml, agreed
rule tests: 50 rules, each with a test named after it
mutation rows: 50, each on the line its rule marks
```

The rest of the gates, and how a change is made, are in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

Apache-2.0.
