# ADR-VI-016: Only a rebase merge, so every commit lands on its own

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

[ADR-VI-015](ADR-VI-015-public-so-the-pull-request-rule-has-a-mechanism.md)
made a pull request the only way onto `main`, which raises a question it did not
answer: what a pull request becomes when it lands.

GitHub offers three. A merge commit writes a commit nobody authored and that
`committed.toml` does not lint — `merge_commit = false` is already set, and the
workflow passes `--no-merge-commit`, so it was never a real option here. A
squash collapses a branch into one commit with a message somebody writes at
merge time. A rebase replays each commit onto `main` unchanged.

The repository already leans one way. `no_fixup` and `no_wip` in
`committed.toml` only make sense if every commit is meant to survive, and
[`CONTRIBUTING.md`](../CONTRIBUTING.md) asks for a message that explains a
change to whoever reads it next — which a squash message, written after the
work and describing several commits at once, is worse at.

## Options considered

**Squash.** A branch can be as messy as it likes and lands as one clean commit.
Genuinely useful when a branch is a day of thrashing. Rejected: it moves the
message to merge time, which is exactly when the reasoning is least fresh, and
it throws away the sequence — the order a change was built in is often the
clearest explanation of why it is shaped that way.

**Squash or rebase, chooser's option.** Rejected as the worst of both: the
history then has two grammars, and which one a commit got depends on who
pressed the button and how tired they were.

**Rebase only.** Accepted.

## Decision

A rebase merge is the only way a pull request lands. Merge commits and squash
are both switched off, and the branch is deleted on merge.

## Consequences

`main` is a linear list of commits each of which was written while its own
change was fresh, each lintable and each meaningful from `git blame`. That is
the history this project's commit conventions were written for.

What gets worse, and it is a real cost on every branch: a branch can no longer
be tidied at the end. Every commit on it lands on `main` individually, so every
commit has to be green and to make sense alone — a half-finished one cannot hide
behind a squash. Work that would naturally be five exploratory commits has to be
rewritten into the two or three that explain the result, and that rewriting is
`git rebase -i` on a branch, which is fiddly and occasionally lossy. The rules
that make this survivable are already in `committed.toml`: no fixups, no
work-in-progress commits.

## Related

[`CONTRIBUTING.md`](../CONTRIBUTING.md),
[ADR-VI-015](ADR-VI-015-public-so-the-pull-request-rule-has-a-mechanism.md).
