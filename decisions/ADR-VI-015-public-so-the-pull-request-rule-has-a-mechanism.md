# ADR-VI-015: Public, so that the pull request rule has a mechanism

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16. Supersedes the "making the
repository public" row in [`deferred.md`](deferred.md), whose trigger had not
fired.

## Context

[`CONTRIBUTING.md`](../CONTRIBUTING.md) has said since the first commit: "Open
one pull request per change." Seven commits went straight to `main` and nothing
objected. That is the defect this repository's own process record,
[ADR-VI-005](ADR-VI-005-how-a-change-is-made.md), exists to prevent: a rule
stated where a reader will find it, enforced by nothing, breaking nothing when
it goes wrong.

The mechanism that would enforce it is branch protection, and GitHub answers a
request for it on this repository with `403: Upgrade to GitHub Pro or make this
repository public`. So the rule could not be given a mechanism while the
repository was private on this account.

The earlier decision to stay private was taken to keep an unproven
specification out of an index until the Linux client had tested its premise.
That reason still holds. What was not known when it was taken is that it also
bought seven unenforced commits, and that the price of the privacy was the
process rule.

## Options considered

**Stay private and correct the guide.** Say that direct pushes to `main` are how
this is actually done, and why: one person, CI on every push, no review to wait
for. Honest, cheap, and it keeps the specification unindexed. Rejected because
it gives up something worth having — a diff that gets looked at before it lands
— to keep a caution whose own trigger is weeks away.

**Stay private and add a `pre-push` hook.** A local hook refusing a push to
`main`. Rejected: `--no-verify` walks past it, the same weakness
[`CONTRIBUTING.md`](../CONTRIBUTING.md) is already honest about for the
commit-msg hook. A gate one person can skip is a gate that person will skip.

**Pay for GitHub Pro.** Buys branch protection on a private repository. Rejected
as a cost with no other benefit here.

**Publish, and turn branch protection on.** Accepted.

## Decision

The repository is public. Branch protection on `main` requires a pull request,
requires every status check to pass, forbids force pushes and deletions,
requires linear history, and applies to administrators too. Secret scanning and
push protection are on, which a public repository also gets for free.

## Consequences

The rule in [`CONTRIBUTING.md`](../CONTRIBUTING.md) becomes true. Every change
from here is a branch, a pull request and a green run before it reaches `main`,
including changes made by an agent, and nobody can decide in the moment that
this one is small enough to skip.

What gets worse, and it is not small. The specification is now indexed with five
open questions still on it, and a specification with open premises reads to a
stranger as a claim rather than as a working document — the reason the earlier
decision went the other way. Publishing cannot be undone: making it private
again does not unpublish it. The design also describes this person's setup,
including that the gateway runs on their laptop and the phone reaches it over
Tailscale; there are no addresses or hostnames in it, and that was checked
before publishing rather than assumed.

One mechanism is still missing, and saying so here is the point. Nothing in the
test suite proves branch protection is on. It is a repository setting, checkable
only against GitHub with a credential, and a test that needs a token to pass is
a test that fails for the wrong reasons. This rule is enforced by a setting, not
by the suite, and [`CONTRIBUTING.md`](../CONTRIBUTING.md) now says so rather
than implying otherwise.

## Related

[`CONTRIBUTING.md`](../CONTRIBUTING.md),
[ADR-VI-005](ADR-VI-005-how-a-change-is-made.md).
