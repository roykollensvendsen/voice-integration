# The phone app

Today's voice page in a small Android app, which keeps the conversation going
with the screen off ([ADR-VI-032](../decisions/ADR-VI-032-the-phone-app-starts-as-the-page-in-a-wrapper.md)).
It adds nothing to what the page does, only what a page cannot have:
- the microphone with the screen locked;
- a notification while it is open;
- a wake lock, so the phone does not sleep under the conversation.

## Build it

Needs Java 17 and Android's tools, with `ANDROID_HOME` pointing at them.

<!-- not run: needs Android's tools; the android job in continuous integration builds it on every change -->
```bash
cd android
./gradlew assembleDebug        # writes app/build/outputs/apk/debug/app-debug.apk
```

## Put it on the phone

Either by cable, with developer options and USB debugging switched on in the
phone's settings:

<!-- not run: installs on the reader's own phone -->
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Or copy the file to the phone, open it, and allow installs from that one
source when Android asks.

The first time it opens, the app asks for the bridge's address. That is the
HTTPS address `tailscale serve` gives, ending in `:10000/`. If the page cannot
be reached later, the app asks again. Android asks once for the microphone and
for notifications.
