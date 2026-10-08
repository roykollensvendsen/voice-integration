# For an assistant setting this up for someone

You are helping a person install voice-integration: a page they talk to, which
can pass what they say on to the Claude Code sessions on their computer or to a
planner. The steps themselves are in the README's "Start here" section. Follow
them there rather than from memory, because continuous integration proves that
section on an empty machine and nothing proves this page.

## Let the check lead

`voicebridge ready --json` lists every check with `ok`, `required`, `detail`
and `fix`. Run it after each step, do the `fix` of the first required check that
fails, and stop when `ready` is `true`. The optional checks say whether the
planner and claude-voice can be reached; the voice works without either.

## What only the person can do

- **Get an OpenAI key.** It is their account and their money. Ask them to make
  one at platform.openai.com/api-keys and put it in
  `~/.config/voice-bridge/env` themselves, or to paste it into a masked prompt
  that writes it there. Never ask them to paste it into the chat.
- **Choose the monthly ceiling.** It is twenty dollars unless they set
  `VOICE_BRIDGE_CEILING_USD`. Raising it is their decision.
- **Change their network.** `tailscale serve`, which puts the page on the
  phone, changes what their devices can reach. Ask first.
- **Take the microphone.** Only a person presses that button.

## What never to do

- **Never print a key.** Neither `OPENAI_API_KEY`, `HERMES_API_KEY` nor
  claude-voice's `CLAUDE_VOICE_TOKEN`. `ready` only says whether each is there
  and accepted; keep it that way in what you write.
- **Never put the page on a public address.** Anyone who can open it can start
  a voice session on the person's key. Tailscale's tailnet-only `serve` is
  fine; `funnel` is not.

## When something fails

- **`ready` is not ready:** do its `fix`.
- **The phone cannot open the page:** the phone is probably asking ordinary
  DNS rather than Tailscale's. Turn on *Use Tailscale DNS* in the Tailscale
  app, and on Android turn *Private DNS* off.
- **The page opens but the microphone is refused:** it was opened over plain
  HTTP from another device. Use the HTTPS address `tailscale serve` gives.
- **A session or the planner does not answer:** `voicebridge ready` names which,
  and the bridge's `/health` address lists the latest errors with the trace id
  of the turn that caused each.
