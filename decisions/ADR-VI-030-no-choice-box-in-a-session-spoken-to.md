# ADR-VI-030: A session spoken to by voice asks out loud, not in a choice box

## Status

Accepted, by Roy Kollen Svendsen, 2026-10-06.

## Context

A Claude Code session can ask its user something in a choice box. Until
somebody answers at the keyboard, the session stands still, and anything sent to
it waits in a queue. On 2026-10-06 the person was talking to one such session by
voice when it opened a box. Three spoken messages queued behind it, the last of
them "I want to say yes". None were read until the box had been answered by
hand, four minutes later.

The voice cannot answer a box. claude-voice can answer a permission question in
a session it runs itself, but not a choice box, and not in a session started in
a terminal. Typing into the terminal from outside works only when the session
happens to run under tmux, and it types into whatever has focus.

## Options considered

**Read the open box aloud and ask the person to answer at the screen.**
claude-voice now reports an open box with its question and choices, and the
bridge says it. Kept, but it only says that the session is stuck; it does not
help the session.

**Type the answer into the terminal.** Rejected: it works for some sessions and
not others, and typing blind into a terminal is not something to do on the
strength of a misheard word.

**Stop the box from opening in the session being spoken to.** Accepted.

## Decision

A hook in the person's own Claude Code settings runs before any choice box
opens, in every session. If the voice bridge has chosen exactly that session as
its target, the box is refused, and the session is told to ask the question in
its reply instead, briefly, with at most two choices in ordinary words. That
reply is read aloud, and the person answers it by speaking. Any other session,
or the same session once the voice has moved on, keeps its boxes.

The bridge keeps the chosen session's id beside its name, because a hook knows
its session only by id.

## Consequences

The session being spoken to never freezes behind a box the person cannot
answer.

What gets worse: this is the first thing from this repository that runs inside
every Claude Code session on the machine, not only beside them. It reads one
small file and allows the box whenever that file is missing or unreadable. A
session that was already running when the hook was installed may not pick it up
until it is restarted.

## Related

[ADR-VI-026](ADR-VI-026-you-choose-who-you-talk-to.md),
`scripts/hooks/no_choice_box_while_spoken_to.py`.
