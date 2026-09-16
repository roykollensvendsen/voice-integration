# ADR-VI-009: Hermes and the bridge run on the laptop, reached over Tailscale

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

Hermes' API server reports `"tool_execution": "server"` and
`"split_runtime": false`. Tools run on the gateway's own host. "Let Claude Code
look at this repository" therefore means Hermes running where the repositories
are, and the repositories are on the laptop — dozens of them, including work in
progress that exists nowhere else.

Against that: the phone has to reach the system from outside the home network,
with the screen locked, while walking.

## Options considered

**Hermes on a VPS, repositories moved there.** Always reachable, no waking, no
tunnel to maintain. Rejected: the agents would then work on copies rather than
on the working tree, and half-finished work on the laptop is exactly what a
person wants an agent to look at.

**Hermes on the laptop, the bridge on a VPS.** The phone always has something to
connect to, and the bridge can say "the machine is asleep" rather than simply
failing. Rejected for now: a third machine in the chain, a second key off the
laptop, and the bridge would have to handle an absent gateway — real complexity
bought for a message.

**Both on the laptop, reached over Tailscale.** Accepted.

## Decision

Hermes and the bridge both run on the laptop. The phone reaches them over
Tailscale. Nothing is exposed to the open internet, and the repositories stay
where they are. The laptop does not sleep while it is on mains power, so that
the phone has something to talk to while the person is out.

## Consequences

The threat model stays small: no public endpoint, no reverse proxy, no
certificate to renew, and the gateway's key never leaves the machine it was
issued for.

What gets worse: the system is exactly as available as one laptop. It sleeps
when the laptop sleeps, and the mains-power rule does not help at all when the
laptop is in the bag. That directly blunts the advantage
[ADR-VI-008](ADR-VI-008-a-native-client-on-each-device.md) paid an Android
application for, and the two decisions were taken knowing it. The honest form of
this is that the phone is for when the machine is standing at home switched on,
and the client should say so rather than time out.

## Related

[`docs/specification.md`](../docs/specification.md),
[ADR-VI-008](ADR-VI-008-a-native-client-on-each-device.md).
