# Permissions

Three layers, and the one invariant that makes them worth having.

## The layers

| Layer | Who enforces it | What it decides | Where it lives |
|---|---|---|---|
| Harness-native | each agent | what this agent can do at all | Claude Code's settings, OpenCode's permissions, Hermes' toolsets and terminal backends |
| Gateway policy | Hermes | what this agent, in this role, in this session, may do now | the gateway's own configuration and its approval queue |
| Voice capabilities | this bridge | which tools this voice session may call, and how it may answer an approval | `voice_bridge.policy` |

They are not alternatives. A harness that enforces its own rules well is still a
harness you have to trust to enforce them, and the gateway exists so that three
different harnesses do not have to be trusted to agree. The voice layer exists
because a channel has its own risks that have nothing to do with the agent at
the other end.

## The invariant

**The voice layer can only ever narrow.**

There is no call in the surface that grants a permission, adds a tool, changes a
policy or raises a role. Not "not exposed yet" — there is no mechanism. If a
permission needs widening, that happens somewhere with a screen and a keyboard,
and the voice plane finds out about it the same way it finds out about
everything else: by asking the gateway.

## Why voice may not say "always"

Hermes accepts four answers to an approval: `once`, `session`, `always` and
`deny`. The bridge sends two.

`session` and `always` both create a standing permission. A standing permission
created through a channel that (a) is often used while walking, (b) routinely
mistranscribes short words, and (c) has no second factor beyond the fact that
somebody is speaking, is a bad trade at any level of convenience. The cost of
getting it wrong is unbounded and deferred; the cost of answering `once` twice
is one extra sentence.

So: **an approval answered by voice binds one call only.** It is a rule in
`voice_bridge.policy`, it has a row in `scripts/mutations.toml`, and switching
it off turns a named test red.

## What a voice session is given

`Capabilities` holds a set of tool names, and every session is constructed with
one. The default is all six, which is right for a person talking to their own
machine and wrong for almost everything else. A session for a second person in
the room, a session started from an unlocked phone, or a session running while
the person is asleep should each be given less.

What none of this does is distinguish *who* is speaking, and that is a decision
rather than a gap. There is no voice identity: claiming the microphone takes a
gesture on an unlocked device, and the unlocked device is the authentication
([ADR-VI-011](../decisions/ADR-VI-011-the-device-is-the-identity.md)). Speaker
verification was considered and refused — a false rejection when the person has
a cold is the kind of annoyance that gets a control switched off, and a false
acceptance is silent.

It follows that this protects nothing against somebody standing at the open
machine, which is why the limit on approval answers above carries more weight
than it otherwise would, and why rooms with more than one person are the last
phase rather than the second.

## What the gateway still owns

Everything that matters. The approval queue is Hermes', keyed per run so that
answering one cannot unblock another. The decision that `git commit` needs an
approval at all is Hermes'. The bridge cannot make a dangerous call safe and
does not try; it can only refuse to be the thing that made it.
