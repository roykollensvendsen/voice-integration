"""Opening a voice session, which is a WebRTC handshake and a budget check.

`gpt-live-1` is reachable over WebRTC and nothing else, so a session is not a
token the page connects with: the page makes an offer, this exchanges it for an
answer, and the audio flows directly between the browser and OpenAI. The key
never reaches the page, which is the only reason this indirection exists.

The session is created in client delegation mode, so the model is given no
functions. What that means for a turn is `docs/voice-contract.md`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from voice_bridge.budget import Ledger
from voice_bridge.policy import Refused

SESSIONS_URL = "https://api.openai.com/v1/live/sessions"
MODEL = "gpt-live-1"
TIMEOUT_SECONDS = 20.0

#: The language the session speaks. It is a setting rather than a constant
#: because the instructions have to be written in it: the prompting guide says
#: to "write your prompt in the language you want the model to speak", and an
#: English prompt is why the first real conversation came back in German.
LANGUAGE = os.environ.get("VOICE_BRIDGE_LANGUAGE", "nb")

#: What each language is called, for a service asked to answer in it.
LANGUAGE_NAMES = {"nb": "norsk", "en": "English"}

#: Five sentences, the same every session so there is nothing to drift. The
#: reasoning is `docs/voice-contract.md`; the words are policy and live here
#: rather than in the page, which is code a browser was handed.
#:
#: This repository is written in English and these are not: they are a prompt,
#: and the guide is explicit that the prompt has to be in the target language.
#: The first line is the rule the guide prescribes, verbatim in shape.
#: The parts the vendor's own prompt guide says to keep for a live voice: how it
#: shows it is listening, what happens when it is interrupted, and when it hands
#: work on. gpt-live-1 has no setting for any of these; the prompt is the only
#: lever. references/voice-ux-research.md.
POLICIES: dict[str, tuple[str, ...]] = {
    "nb": ("Lytting:", "Avbrytelse:", "Delegering:", "Variasjon:"),
    "en": ("Listening:", "Interruption:", "Delegation:", "Variety:"),
}

INSTRUCTIONS: dict[str, str] = {
    "nb": (
        "Snakk norsk med mindre brukeren ber om noe annet. "
        "Du er stemmen til et agentsystem, ikke agenten selv. "
        "Du har ingen verktøy selv, men bak deg står et system som kan kjøre kodeagenter "
        "som Claude Code og OpenCode, lese og endre filer, kjøre kommandoer, søke på nettet "
        "og si hva klokka er. Si aldri at du ikke har verktøy, agenter eller tilgang til "
        "noe — si hva systemet kan, og be bakenden om det. "
        "Svar selv på småprat, allmennkunnskap og spørsmål om deg selv eller samtalen. "
        "Spør bakenden bare når brukeren vil ha noe gjort på maskinen — kode, filer, "
        "kommandoer, agenter. Bestem aldri selv hva som skal gjøres der. "
        "Les aldri opp en identifikator, en filsti eller et tidsstempel. De står på skjermen. "
        "Si det bakenden gir deg, og stopp.\n"
        "Lytting: Lytt videre når personen tar en pause for å tenke; et kort opphold er ikke "
        "slutten på det de sier. Svar aldri før de er ferdige med tanken: et «eh» eller «øh», en "
        "halv setning, eller en setning som slutter på «og», «men», «altså» eller «så», betyr at de "
        "ikke er ferdige, så vent. Er du i tvil, vent litt til. Vis at du følger med med en kort lyd "
        "en sjelden gang, ikke hele tiden.\n"
        "Avbrytelse: Blir du avbrutt, slutt å snakke med en gang og lytt. «Stopp» betyr at du "
        "skal tie. «Avbryt» betyr at arbeidet som er i gang skal stoppes; be bakenden om det. "
        "«Legg på» eller «avslutt samtalen» betyr at samtalen skal avsluttes. Bare bakenden kan "
        "legge på, så be den om det, og si aldri at du legger på uten å ha spurt.\n"
        "Delegering: Be bakenden om hjelp før du gir et svar som avhenger av den. Si én kort "
        "setning om at du er i gang når du sender videre, og gjett aldri på resultatet mens du venter. "
        "Lov aldri hvor lang tid noe tar. Si aldri at noe er gjort før bakenden har sagt det. "
        "Hvem personen snakker med, hvilke økter som finnes og hjelp til å bytte, spør du alltid "
        "bakenden om.\n"
        "Variasjon: Bruk aldri samme formulering to ganger på rad. Si det kort, og si det på en "
        "ny måte hver gang."
    ),
    "en": (
        "Speak English unless the user asks to switch. "
        "You are the voice of an agent system, not the agent. "
        "You have no tools yourself, but behind you is a system that runs coding agents "
        "such as Claude Code and OpenCode, reads and changes files, runs commands, searches "
        "the web and tells the time. Never say you have no tools, no agents or no access to "
        "something — say what the system can do, and ask the backend for it. "
        "Answer small talk, general knowledge and questions about yourself or this "
        "conversation on your own. Ask the backend only when the person wants "
        "something done on the machine — code, files, commands, agents. Never decide "
        "what happens there yourself. "
        "Never read out an identifier, a file path or a timestamp. They are on the screen. "
        "Say what the backend gives you, then stop.\n"
        "Listening: Keep listening while the person pauses to think; a short pause is not the "
        "end of what they are saying. Never answer before they have finished the thought: an "
        '"um", a half sentence, or one ending in "and", "but" or "so" means they are not '
        "done, so wait. When unsure, wait a little longer. Show you are following with a short "
        "sound now and then, not constantly.\n"
        'Interruption: When interrupted, stop speaking at once and listen. "Stop" means be '
        'quiet. "Cancel" means the work under way should stop; ask the backend for that. '
        '"Hang up" or "end the call" means the call should end. Only the backend can hang up, '
        "so ask it, and never say you are hanging up without having asked.\n"
        "Delegation: Ask the backend before giving an answer that depends on it. Say one short "
        "line that you are on it when you hand work on, and never guess the result while waiting. "
        "Never promise how long something takes. Never say something is done before the backend "
        "has said so. Whom the person talks to, which sessions there are, and help with switching "
        "are always asked of the backend.\n"
        "Variety: Never use the same phrasing twice in a row. Keep it short, and say it a "
        "new way each time."
    ),
}


#: What the model is told to say while the backend works. Written in each
#: language for the same reason the instructions are: a prompt is in the
#: language it produces. Without it a slow answer is silence, and silence on a
#: phone call is indistinguishable from a dropped one.
#: A fact for the voice to know while it waits, not a line to say: sent as a
#: line to say, "Si kort at du setter i gang, og vent" was read out word for word.
HOLDING: dict[str, str] = {
    "nb": "Bakenden jobber fortsatt med dette; ingenting er ferdig ennå.",
    "en": "The backend is still working on this; nothing is finished yet.",
}


#: What the model is told, quietly, once the browser says where the person is.
#: It is a fact to have rather than a thing to say, which is what
#: `session.thinking.append` is for.
#:
#: Without it the voice denied having a position while the page displayed it,
#: two hand-spans away — and it denied it without asking anybody, because
#: "do you have my position" reads as a question about itself and it answers
#: those alone. A fact it holds is the only fix; being told to go and ask is
#: not, since it does not think there is anything to ask about.
KNOWN_PLACE: dict[str, str] = {
    "nb": "Brukeren er i {place}. Det vet du, og du kan svare på det uten å spørre bakenden.",
    "en": "The person is in {place}. You know this, and can answer from it without asking the backend.",
}


#: What counts as answering a permission question. Nothing outside these lists
#: is treated as an answer: a channel that mishears short words must not guess
#: at a yes, and ADR-VI-003 already limits a spoken answer to this one call.
YES: dict[str, tuple[str, ...]] = {
    "nb": ("ja", "ja takk", "greit", "kjør", "kjør det", "gjør det", "ok", "okay"),
    "en": ("yes", "yes please", "go ahead", "do it", "run it", "ok", "okay"),
}
NO: dict[str, tuple[str, ...]] = {
    "nb": ("nei", "nei takk", "stopp", "ikke", "la være", "avbryt"),
    "en": ("no", "no thanks", "stop", "don't", "do not", "cancel"),
}


def answer_to_a_question(said: str, language: str | None = None) -> str | None:
    """`once`, `deny`, or None when that was not an answer at all."""
    spoken = said.strip().strip(".!?,").casefold()
    chosen = language or LANGUAGE
    if spoken in YES.get(chosen, ()) or spoken in YES["en"]:
        return "once"
    if spoken in NO.get(chosen, ()) or spoken in NO["en"]:
        return "deny"
    return None


def known_place(place: str, language: str | None = None) -> str:
    """What to tell the model, quietly, about where the person is."""
    said = KNOWN_PLACE.get(language or LANGUAGE, KNOWN_PLACE["en"])
    return said.format(place=place)


def holding(language: str | None = None) -> str:
    """What to say while the work runs."""
    return HOLDING.get(language or LANGUAGE, HOLDING["en"])


def instructions(language: str | None = None) -> str:
    """The session instructions, in the language the session speaks."""
    chosen = language or LANGUAGE
    # RULE: a session is never opened without a language rule in its own language
    if chosen not in INSTRUCTIONS:
        message = f"no instructions written in {chosen!r}; the prompt must be in the language it speaks"
        raise Refused(message)
    return INSTRUCTIONS[chosen]


#: How much of the last conversation a new session is given. `input` is a
#: startup field — the guide is explicit that it cannot replace history in a
#: running session — so this is the one chance to resume a topic. It is bounded
#: because a voice session should hold the last few turns and not a diary.
TURNS_REMEMBERED = 12


#: The voices the service accepts, checked by calling it:
#: evidence/api/gpt-live-1-transport-and-delegation.md. An unknown name is read
#: as a custom voice and refused with a 403.
VOICES = (
    "marin",
    "cedar",
    "quartz",
    "ripple",
    "vesper",
    "willow",
    "stone",
    "gleam",
    "meridian",
    "bossa",
    "tempo",
    "beacon",
    "delta",
    "cinder",
)


#: What the page says it is running in, in the words the voice would use.
CLIENTS = {
    "nb": {
        "android-app": "telefonappen på Android-telefonen",
        "phone-browser": "nettleseren på telefonen",
        "browser": "nettleseren på maskinen",
    },
    "en": {
        "android-app": "the phone app on the Android phone",
        "phone-browser": "the browser on the phone",
        "browser": "the browser on the computer",
    },
}


def whereabouts(client: str | None, language: str | None = None) -> str:
    """What the voice should know about where it runs, and where its time and place come from.

    Asked where it got the time from, and on which device it ran, it did not know.
    """
    if (language or LANGUAGE) == "en":
        where = CLIENTS["en"].get(str(client), "a device the page did not name")
        return (
            f"About yourself: the person is talking to you from {where}. The time the backend gives "
            "comes from the computer the bridge runs on, and the position from the GPS of the device "
            "the person speaks from. If asked where you run, or where the time or the position comes "
            "from, say so."
        )
    where = CLIENTS["nb"].get(str(client), "en enhet siden ikke har oppgitt")
    return (
        f"Om deg selv: Personen snakker med deg fra {where}. Klokka bakenden gir deg, kommer fra "
        "maskinen der broen kjører, og posisjonen fra GPS-en på enheten personen snakker fra. Spør "
        "personen hvor du kjører, eller hvor klokka eller posisjonen kommer fra, så si det."
    )


def session_config(
    language: str | None = None,
    history: list[dict[str, object]] | None = None,
    voice: str = "marin",
    steer: str = "",
    about: str = "",
) -> dict[str, object]:
    """What the session is created with, and deliberately nothing more."""
    return {
        # Fixed for the life of the session; a new voice means a new session.
        "audio": {"output": {"voice": voice}},
        "input": list(history or [])[-TURNS_REMEMBERED:],
        "model": MODEL,
        # Client delegation: the backend is ours, so the Live session is told
        # about no tools at all. ADR-VI-019 is why.
        "delegation": {"type": "client"},
        "instructions": "\n\n".join(part for part in (instructions(language), steer, about) if part),
    }


def open_session(  # noqa: PLR0913 — the voice joined five that each change what is opened
    offer_sdp: str,
    ledger: Ledger | None = None,
    key: str | None = None,
    language: str | None = None,
    history: list[dict[str, object]] | None = None,
    *,
    voice: str = "marin",
    steer: str = "",
    about: str = "",
) -> str:
    """Exchange the page's offer for an answer, or refuse and say why."""
    # RULE: the month is checked before a session is opened
    (ledger or Ledger()).authorise()
    token = key if key is not None else os.environ.get("OPENAI_API_KEY", "")
    if not token:
        message = "no OPENAI_API_KEY, so no voice session can be opened"
        raise Refused(message)
    body = json.dumps(
        {
            "transport": {"type": "webrtc", "sdp": offer_sdp},
            "session": session_config(language, history, voice, steer, about),
        }
    )
    request = urllib.request.Request(
        SESSIONS_URL,
        data=body.encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 — as above
            answer = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as failure:
        error = json.loads(failure.read() or b"{}").get("error", {})
        detail = error.get("message", "no detail")
        message = f"OpenAI refused the session: {detail}"
        if error.get("code") == "insufficient_quota":
            # The bridge's own ceiling knows nothing of the account, which ran dry
            # while the page still showed minutes left.
            message = (
                "The OpenAI account has no credit left. Top it up at platform.openai.com/settings/billing."
            )
        raise Refused(message) from failure
    sdp = _answer_sdp(answer)
    if not sdp:
        message = f"no answer in the session OpenAI created: {sorted(answer)}"
        raise Refused(message)
    return sdp


def _answer_sdp(answer: dict[str, object]) -> str:
    """The answer, wherever the reply happens to carry it."""
    transport = answer.get("transport")
    if isinstance(transport, dict) and isinstance(transport.get("sdp"), str):
        return str(transport["sdp"])
    return str(answer["sdp"]) if isinstance(answer.get("sdp"), str) else ""
