# ADR-VI-006: The bridge has no runtime dependencies

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16. Superseded by [ADR-VI-018](ADR-VI-018-the-client-is-a-browser-page.md) the same day: the bridge serves the browser client, so it needs a web framework.

## Context

This process is the only one reachable from both the audio provider and the
gateway, and it holds the gateway's API key. Everything in its import graph is
in the path between a microphone and a shell on a machine with repositories on
it.

The work it does is small: build a URL, post some JSON, read some JSON back, cut
a string to length. The standard library does all of it.

## Options considered

**`httpx` or `requests`.** Better ergonomics, retries, connection pooling, and a
dependency tree that is not small. Rejected for now: nothing here needs pooling,
and the request count per minute is in single digits.

**`pydantic` for the tool schemas.** Validation for free and a schema generator.
Rejected: the six schemas are forty lines of dictionaries that a person can read
and a reviewer can check, and the validation that matters is the gateway's.

**No runtime dependencies.** Accepted.

## Decision

`dependencies` in `pyproject.toml` stays empty. Development dependencies —
pytest, ruff, mypy — are unconstrained by this.

## Consequences

`uv sync` is fast, the lock file is short, and the supply-chain surface of the
process holding the key is the standard library and nothing else. Reading the
whole thing before trusting it is a realistic afternoon.

What gets worse: the audio client in phase two cannot honour this. A WebRTC or
WebSocket client against the Realtime API is not something to write by hand.
When it lands, it goes behind an optional extra so that the part holding the key
and the part holding the microphone do not share an import graph by default —
and this record is superseded rather than quietly broken.

## Related

[`docs/specification.md`](../docs/specification.md),
[`decisions/deferred.md`](deferred.md).
