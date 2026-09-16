# ADR-VI-001: Hermes is the control plane

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

The design started as "build a gateway": something holding sessions, routing to
Claude Code, OpenCode and DeepSeek Harness, enforcing permissions, collecting
events and asking a person for approval. Partway through it became clear that
Hermes Agent already is that process.

Read against the source at `NousResearch/hermes-agent`, its `api_server`
platform adapter serves, on port 8642 behind `API_SERVER_KEY`:

* `POST /v1/runs`, answering `202` with a `run_id` before the work is done
* `GET /v1/runs/{run_id}` for pollable status, and `/events` for a server-sent
  lifecycle stream
* `POST /v1/runs/{run_id}/approval`, with approval queues keyed per run so that
  answering one cannot unblock another
* `POST /v1/runs/{run_id}/steer` and `/stop`
* session create, list, read, update, fork and continue under `/api/sessions`
* an OpenAI-compatible `/v1/chat/completions` and `/v1/responses` besides

It also has the parts underneath: toolsets that can be switched per session,
seven terminal backends including Docker and SSH, A2A messaging, an MCP server,
subagents, and a cron scheduler.

## Options considered

**Build our own gateway.** Full control over the session and permission model,
and a shape designed for voice from the start. Rejected: it is months of the
least interesting work in the project, and every one of those months is spent
re-deriving decisions Hermes has already made and tested. The conversation that
led here reached the same conclusion out loud.

**Use OpenCode as the orchestrator.** Strong sub-agent support and detailed
permissions, and the most practical integration with existing coding agents.
Rejected as the control plane because its centre of gravity is a coding session,
not a multi-party, multi-session control surface with an approval queue.

**Use DeepSeek Harness as the orchestrator.** A plugin-based runtime with
traceable sessions, and the most experimentally interesting of the three.
Rejected for the same reason, plus: model access there normally goes through a
provider API, so it is a worker with a bill, not a free control plane.

**Do nothing — talk to each agent separately.** Rejected because it is the
problem: three harnesses, three permission models, three places to look, and no
way to ask what is happening.

## Decision

Hermes Agent's gateway is the control plane. This repository builds only the
voice edge in front of it, and Claude Code, OpenCode and DeepSeek Harness are
workers reached through it.

## Consequences

The bridge stays small enough to read in one sitting, and every hard problem —
sessions, approvals, routing, events — is solved by something already tested.

What gets worse: this project now has a dependency it does not control, on a
fast-moving repository, with no stability guarantee on the API it consumes.
`docs/hermes-contract.md` exists to make a break loud rather than mysterious,
and `GET /v1/capabilities` is called rather than assumed. A second consequence
is placement: Hermes' API server executes tools on its own host
(`"tool_execution": "server"`), so wherever the gateway runs is where the
agents' hands are — which is open question 4 and not settled here.

## Related

[`docs/specification.md`](../docs/specification.md),
[`docs/hermes-contract.md`](../docs/hermes-contract.md).
