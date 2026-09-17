# ADR-VI-020: Reach a coding agent in print mode, not through its screen

## Status

Accepted, by Roy Kollen Svendsen, 2026-09-17. Superseded by [ADR-VI-021](ADR-VI-021-a-resumable-print-session.md) the same day: the cost this record accepted — an agent that starts over every time — turned out not to be real.

## Context

Claude Code can be reached two ways. Print mode takes one question, answers it
on standard output, and exits. Interactive mode is a terminal application: you
start it inside `tmux`, type into it, and read its screen back with
`capture-pane`.

The gateway's own guide prefers print mode and documents both. Asked for a
session that could be talked to over time, it reached for the interactive one.
That failed five times in a row, in five different ways, and every one of them
was found and written into the guide:

* `send-keys` against a tmux server that was never started
* the workspace-trust dialog, whose safe option is selected first, so the
  documented "press Enter" quits the agent immediately
* a multi-line prompt with `Enter` in the same call, which leaves the text in
  the input box unsent while the session looks alive
* the screen captured before the agent has answered, returning the *previous*
  answer, which is indistinguishable from silence
* `capture-pane` returning a stale screen entirely, because a pane with no
  client attached can lag behind what the program drew — forty backspaces
  appeared to do nothing until the window was resized

After all five were corrected in the guide, it failed again, because the
gateway decides for itself when to read and did not wait.

The same question in print mode answered correctly every time, including
through the whole voice chain: "det virker", first try, while the interactive
path was still reporting nothing.

## Options considered

**Keep fixing the interactive path.** Each failure had a real cause and a real
fix, and the guide is better for having them. Rejected: the last failure was not
a missing instruction but a judgement call about when to look, made by a model.
Screen-scraping a terminal application through something that chooses its own
timing cannot be made reliable by writing more guidance.

**Have the bridge drive the session itself**, with the timing in code rather
than in a prompt. It would work. Rejected: it puts the bridge in the business of
parsing a terminal user interface, and it goes around the control plane, which
[ADR-VI-001](ADR-VI-001-hermes-is-the-control-plane.md) exists to prevent.

**Print mode.** Accepted.

## Decision

A spoken request reaches a coding agent in print mode: one question, one answer,
read from its output. An interactive session is started only when the person
asks for one to use themselves.

## Consequences

Five failure modes disappear at once. There is no dialog to answer, no input box
that can hold stale text, no screen to scrape and no screen that can be stale.
The answer is the answer.

What gets worse, and it is the reason interactive was attractive: every question
starts the agent again. It re-reads the project each time, which is most of the
two and a half minutes a real question takes, and it remembers nothing from the
last one. Continuity lives in the gateway's room instead
([ADR-VI-013](ADR-VI-013-the-room-is-the-memory-scope.md)), which holds the
conversation but not the agent's own working state.

This is also a decision about somebody else's software that may stop being true.
If the interactive path becomes reliable — a completion signal on the stream, or
an interface that is not a screen — this record is the one to revisit.

## Related

[`docs/specification.md`](../docs/specification.md),
[ADR-VI-001](ADR-VI-001-hermes-is-the-control-plane.md).
