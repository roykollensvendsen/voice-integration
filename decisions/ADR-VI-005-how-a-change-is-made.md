# ADR-VI-005: How a change is made here

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-16.

## Context

This repository is mostly specification, and it will be worked on by agents as
much as by people. Both of those facts point the same way: the documents are the
artefact, and a document that has quietly stopped being true is worse than no
document, because it is still believed.

The failure is well enough known to have a shape. A guide names gates nobody
runs. A page shows a command nobody can run. A tool enforces a rule the
specification never states. Each reads as rigour, holds nothing, and breaks
nothing when it goes wrong — which is why it survives.

## Options considered

**Review and discipline.** What most repositories do. Rejected: it works until
the week it matters, and it does not work at all for an agent writing the next
change at three in the morning.

**A documentation site with generated API reference.** Solves a different
problem. The facts that go stale here are not signatures; they are claims about
what is enforced and what another system's API does.

**Every restated fact gets a mechanism that fails.** Accepted.

## Decision

1. **Say it before you build it.** A rule, a flag or a field is written into
   `docs/` before it is code. If the documentation does not say it, it is not
   decided.
2. **Every fact stated twice is compared.** The voice tools, the gateway paths
   and the rule list are each written in prose and in code, and
   `voicebridge check` fails the build when a pair disagrees.
3. **Every example is run.** A block fenced ` ```console ` is executed by
   `tests/test_documented_commands.py` and its output compared with the page. A
   block that looks like commands and is not run says in the document why.
4. **Every rule has a mutation row.** A rule marked `# RULE:` in the source has
   a row in `scripts/mutations.toml`; switching it off must turn a named test
   red. `voicebridge check` compares the two sets, so the evidence cannot fall
   behind the code.
5. **Decisions that cost more to reverse than to take are written here first.**

## Consequences

Adding a voice tool means editing a table, a tuple and a test, and a pull
request that does two of the three fails. That is the point, and it is also
friction on every change.

What gets worse: the check is a mechanism that can itself be wrong. A mutation
can kill a test for an incidental reason and leave a rule looking guarded when
it is not, so a kill is read as carefully as a survival — the expected test has
to be the one that went red.

## Related

[`CONTRIBUTING.md`](../CONTRIBUTING.md),
[`docs/specification.md`](../docs/specification.md).
