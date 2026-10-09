# A phone app for the voice: a proposal

*Draft for Roy to say yes or no to, 2026-10-09. Nothing here is built yet. The phone is an Android phone (Roy, 2026-10-09).*

## What it is for

Today the voice lives in a browser page. That works at the desk, and on the
phone while the screen is on. It stops being useful the moment the phone goes
into a pocket. You asked for six things the page cannot do:

1. **Keep talking with the screen locked.** A walk, a drive, the phone in a
   pocket, and the conversation carries on.
2. **Start when you speak to it.** No button, no unlocking: say a wake word,
   and the voice is there.
3. **Cost nothing until then.** The paid voice session opens only after the
   wake word, and closes again after a quiet spell.
4. **Know where you are.** Your position can be passed to the sessions when it
   matters, as the page already does once per session.
5. **Live alongside podcasts.** The voice pauses Spotify when you speak to it,
   answers, and resumes the episode. You can also ask what the episode is about.
6. **Call people by name.** "Ring Kari" finds Kari in your contacts and rings
   her.

A seventh follows from the first: **echo separation**. With the speaker on and
a podcast playing, the voice must not mistake its own answer, or the podcast,
for you speaking.

## Why a browser page cannot do it

A page loses the microphone when the screen locks or the browser goes to the
background. It cannot listen for a wake word without keeping an open,
billed voice session. And it cannot read contacts, place calls or pause another
app's audio. Each of these needs a native app.

## What I propose

A small native app that does only what the page cannot. Everything else stays
where it is today: the bridge on the laptop and the sessions it talks to. The
app is a second client, alongside the page, and talks to the same bridge over
Tailscale.

| Need | How the app does it |
|---|---|
| Locked screen | A background service that keeps the microphone and the voice connection while the screen is off, with the notification the phone requires for it |
| Wake word | A small detector running on the phone itself, such as openWakeWord. It listens only for the wake word. No audio leaves the phone until the wake word is heard |
| Costs nothing until then | The paid voice session opens on the wake word, and closes after a quiet spell, say 30 seconds, as the page already does |
| Location | Sent to the bridge on the wake word, as the page does now, and held in memory only |
| Podcasts | Pause and resume through the phone's standard media controls, which Spotify follows. To ask what an episode is about, the app reads its title and the bridge looks it up |
| Stop–ask–resume | Speaking pauses what is playing. The answer is read, and playback resumes on its own |
| Echo separation | The phone's own echo cancellation, which a native app can switch on explicitly |
| Calling by name | Contacts are read on the phone, and the call is placed by the phone. The bridge never sees the address book |

## What it changes in decisions already taken

**[ADR-VI-010](../decisions/ADR-VI-010-one-live-microphone.md) says the
microphone opens only on a deliberate act.** A wake word is a deliberate act,
but a spoken one. A podcast or a television could in principle say something
close to it. I propose a new decision record to amend ADR-VI-010, with three
parts:

- the wake word is the deliberate act;
- the wake-word detector never sends audio anywhere;
- a false start costs at most one short session, which closes on silence.

The rule that only one client holds the microphone at a time stays as it is.
A wake word on the phone takes the microphone from the page.

## What I do not know yet

- **Which phone: settled, Android.** Android allows every part of this,
  including a microphone with the screen locked and placing a call without a
  tap, once you have allowed each in the app.
- **How well wake words work outdoors.** A detector on the phone mishears in
  wind and traffic more than at a desk. I would measure that on the first
  build, before relying on it.
- **Spotify's own controls.** Plain play and pause work for every player
  through the phone's media controls. Asking about the episode needs its
  title, which Spotify shares, and the rest is the bridge's work.

## How it reaches your phone

The app is built on the laptop, which already has Android's tools, and is not
published in any store. You install it once by cable or as a file, after
allowing installs from this one source on the phone, and later versions
replace it the same way. Android then asks you, one at a time, for the
microphone, contacts, calls and location. Each is your yes, and each can be
taken back in the phone's settings.

## The order I would build it in

1. Locked screen, with a button to start talking. That is today's page, but in
   the pocket.
2. The wake word, on the phone, with the session opening only on it.
3. Pause and resume around podcasts, then asking what the episode is about.
4. Calling by name.
5. Location on the wake word.

Each step is used for real before the next is begun. Steps 1 and 2 are where
the value is, and where the cost is saved.
