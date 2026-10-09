"""Who a turn goes to: the voice alone, the gateway, or one Claude Code session.

The person chooses, by tapping a tree on the page or by saying so, and the
choice stays until they change it. The reason is theirs, in two words: cost and
response. The voice alone is free and instant; the gateway is a model call of
about ten seconds; one session is about five seconds on the subscription.
ADR-VI-026.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
from dataclasses import dataclass
from typing import Any

from voice_bridge.live import VOICES

#: The three kinds of target there are.
KINDS = ("voice", "hermes", "session")

#: Longer than this and "talk to" is part of a sentence about something else.
SHORTEST_IS_SAFEST = 60

# Said on 2026-10-08 and sent to the planner, which could not help: "kan du
# sette meg over til …-økta", "jeg vil gå tilbake til å bare prate med GPT Live
# One". A switch is a way of moving, then whoever it is to.
_MOVE = re.compile(
    r"^(?:(?:gå )?tilbake til(?: å)?(?: bare)?(?: (?:snakke|prate) med)?|go back to"
    r"|sett(?:e)? (?:meg )?over til|koble?(?:e)? meg (?:til|på)|connect me to|bytt(?:e)? til|switch to"
    r"|gå over til|hopp(?:e)? (?:over )?til|start(?:e)? (?:en )?samtale(?:n)? med"
    r"|(?:snakk(?:e)?|prat(?:e)?|talk|speak) (?:med|to|with))\s+(?:the\s+)?(.+)$"
)
_KIND_WORD = r"(?:[ -]?(?:økta|økten|økt|økte|session))?"
_TO_VOICE = re.compile(
    r"(?:bare )?(?:stemmen|stemme|stemmelaget|voice|jarvis|deg|you|gpt[ -]?live(?:[ -]?(?:one|1|en))?)"
    + _KIND_WORD
)
_TO_HERMES = re.compile(r"hermes" + _KIND_WORD)
# "Hei Hermes", which the voice itself suggests. Only for Hermes: "hei" before
# anything else is a greeting, not a wish to talk to someone else.
_GREETING = re.compile(r"^(?:hei|hallo|hey|hi|hello),?\s+")
# "en Claude Code-økt": a session, but which one was not said.
_ANY_SESSION = re.compile(r"(?:en |ei |a )?(?:claude(?:[ -]?code)?|kode)?" + _KIND_WORD)
_FILLER = re.compile(r"\b(?:ehm|eh|øh|hmm)\b")
_ASKING = re.compile(
    r"^(?:ok(?:ei)?|ja|men|så|og|altså|kan du(?: stemmen)?|kan vi|la oss|jeg (?:vil|ønsker å|skal)"
    r"|i want to|can we|can you|please)\s+"
)
_TRAILING = re.compile(r"[\s-]*(?:igjen|igen|again|nå|now|takk|thanks)?[\s-]*$")
_SESSION_WORD = re.compile(r"^(?:økta|økten|session)\s+|[\s-]+(?:økta|økten|session)$")
_NOT = re.compile(r"\b(?:ikke|not|don't|do not)\b")


#: Who speaks for each kind of target until the person picks otherwise, so that
#: a voice tells you who is answering. ADR-VI-027.
VOICE_DEFAULTS = {"voice": "marin", "hermes": "cedar", "session": "quartz"}

_WHICH_VOICES = re.compile(r"^(?:hvilke stemmer|which voices|what voices|list (?:the )?voices)")
# Searched for anywhere in a short sentence: "kan du bytte stemme til ripple da"
# was otherwise taken for a request to somebody else.
_CHANGE_VOICE = re.compile(
    r"\b(?:bytt|bytte|endre|skift|change|switch)\s+(?:stemme|stemmen|the voice|voice)\s+(?:til|to)\s+(\w+)"
    r"|\b(?:bruk|use)\s+(?:stemmen|the voice)\s+(\w+)"
)


@dataclass(frozen=True)
class Target:
    """Where a turn the bridge cannot answer itself is sent."""

    kind: str
    name: str = ""

    def said(self) -> str:
        """Who this is, in words a person hears."""
        if self.kind == "voice":
            return "Jarvis alone"
        if self.kind == "hermes":
            return "Hermes"
        return self.name

    def as_json(self) -> dict[str, str]:
        """The shape the page and the state file take."""
        return {"kind": self.kind, "name": self.name} if self.kind == "session" else {"kind": self.kind}


def state_file() -> pathlib.Path:
    """Where `voicebridge serve` keeps the choice between runs."""
    base = os.environ.get("XDG_STATE_HOME") or str(pathlib.Path.home() / ".local" / "state")
    return pathlib.Path(base) / "voice-bridge" / "target.json"


def load(path: pathlib.Path | None) -> Target:
    """The choice made last time, or the gateway when there was none."""
    if path is None:
        return Target("hermes")
    try:
        kept = json.loads(path.read_text())
    except (OSError, ValueError):
        return Target("hermes")
    kind = str(kept.get("kind", "")) if isinstance(kept, dict) else ""
    if kind not in KINDS or (kind == "session" and not kept.get("name")):
        return Target("hermes")
    return Target(kind, str(kept.get("name", "")) if kind == "session" else "")


def save(path: pathlib.Path | None, chosen: Target, session_id: str = "") -> None:
    """Keep the choice where a restart, and the chosen session's own hooks, will find it."""
    if path is None:
        return
    kept: dict[str, str] = chosen.as_json()
    if chosen.kind == "session" and session_id:
        # A name can change and need not be unique; a hook knows its session by id.
        kept["claude_session_id"] = session_id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(kept))


#: Said to the voice whoever it speaks for: it once answered "Ja, da bytter jeg
#: til Ripple nå" by itself, and nothing changed.
_ASK_TO_CHANGE = (
    " Vil personen bytte stemme eller hvem de snakker med, be alltid bakenden om hjelp, "
    "og si ikke at det er gjort før svaret kommer."
)


def steer(chosen: Target) -> str:
    """What the voice is told about who it speaks for, so it knows when to ask.

    The voice decides for itself when to ask the bridge, and it answered most
    things itself: with a session chosen, that session saw almost nothing of
    what was said. So the voice is told, every time the target changes, whether
    it answers or only carries words to somebody else.
    """
    if chosen.kind == "session":
        return (
            f"Du er nå bare en stemme for Claude-økta {chosen.name}. Alt personen sier, er til "
            f"{chosen.name}: be alltid bakenden om hjelp, uansett hva det gjelder, og svar aldri selv. "
            "Les opp det som kommer tilbake, med dine egne ord og kort. Si ingenting eget før "
            "svaret kommer, og aldri hvordan du fant det: ikke «ja», ikke «jeg sjekker», og ikke "
            "at du spurte noen. "
            # Asked "you are not the Claude session, are you?", it said "Yes, I
            # am", and could not say why it sounded different from before.
            f"Bare om personen spør hvem du er: du er stemmen, ikke {chosen.name}; du bærer ordene "
            "fram og tilbake. Hver samtalepartner har sin egen stemme, så den skifter når de bytter."
            + _ASK_TO_CHANGE
        )
    if chosen.kind == "hermes":
        return (
            "Du snakker nå på vegne av Hermes, som styrer kodeagentene. Be bakenden om hjelp med alt "
            "som gjelder arbeid, filer, økter eller noe du ikke vet sikkert; småprat svarer du selv."
            + _ASK_TO_CHANGE
        )
    return (
        "Personen vil nå snakke med deg alene: svar selv, og be ikke bakenden om hjelp. Unntak: når "
        "personen svarer ja eller nei på et spørsmål om tillatelse, vil vite klokka eller hvor de er, "
        "eller vil bytte til Hermes eller en økt, skal du be bakenden om hjelp." + _ASK_TO_CHANGE
    )


def voices_file(chosen_file: pathlib.Path | None) -> pathlib.Path | None:
    """Where the voices are kept: beside the target."""
    return None if chosen_file is None else chosen_file.with_name("voices.json")


def load_voices(path: pathlib.Path | None) -> dict[str, str]:
    """The voices picked last time, or the defaults."""
    voices = dict(VOICE_DEFAULTS)
    if path is None:
        return voices
    try:
        kept = json.loads(path.read_text())
    except (OSError, ValueError):
        return voices
    if isinstance(kept, dict):
        voices.update({k: v for k, v in kept.items() if k in VOICE_DEFAULTS and v in VOICES})
    return voices


def save_voices(path: pathlib.Path | None, voices: dict[str, str]) -> None:
    """Keep the voices where a restart will find them."""
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(voices))


def voice_request(said: str) -> str | None:
    """Whether this asks for the list of voices ("list") or for a new one (its name), or neither."""
    words = said.strip().strip(".!?,").casefold()
    if len(words) > SHORTEST_IS_SAFEST:
        return None
    if _WHICH_VOICES.match(words):
        return "list"
    found = _CHANGE_VOICE.search(words)
    return (found.group(1) or found.group(2)) if found else None


#: "Avbryt" stops the work under way. A bare "stopp" only quiets the voice, which
#: the voice does by itself; it never reaches here as a cancel.
_CANCEL = re.compile(
    r"^(?:avbryt|cancel|stopp arbeidet|stopp jobben|stop the work|stop the job)"
    r"(?:\s+(?:det|det der|alt|that|it|everything))?$"
)


# "Kan du stoppe pengebruken nå? Be også putt down microphone", said on the
# phone on 2026-10-09: hang up, so that nothing more is paid for.
_HANG_UP = re.compile(
    r"^(?:(?:du kan )?(?:bare )?(?:jeg )?legg(?:e|er)? på(?: røret| telefonen)?(?: nå)?(?: midlertidig)?|"
    r"hang up|end the call|"
    r"put(?:t)?(?: it)? down(?: the)?(?: microphone)?|"
    r"(?:be (?:også )?)?put(?:t)? down(?: the)? microphone|legg(?:e)? (?:ned|fra deg) mikrofonen|"
    r"slå av stemmen|stopp(?:e)? stemmen|stopp(?:e)? pengebruken|avslutt(?:e)? samtalen?)$"
)


#: "Sett lyden til 30 prosent", asked for on 2026-10-09: the number is often
#: written as a word by the transcriber.
_VOLUME_WORDS = {
    "null": 0,
    "fem": 5,
    "ti": 10,
    "femten": 15,
    "tjue": 20,
    "tjuefem": 25,
    "tretti": 30,
    "førti": 40,
    "femti": 50,
    "seksti": 60,
    "sytti": 70,
    "åtti": 80,
    "nitti": 90,
    "hundre": 100,
}
_VOLUME = re.compile(
    r"\b(?:lyden|lydnivået|lydstyrken|volumet|the volume|volume)\b.{0,20}?\b(?:til|på|to)\s+"
    r"(\d{1,3}|" + "|".join(_VOLUME_WORDS) + r")\b"
)
_LOUDER = re.compile(r"\b(?:skru|sett) opp lyden\b|\bhøyere lyd\b|\bturn (?:it|the volume) up\b")
_SOFTER = re.compile(r"\b(?:skru|sett) ned lyden\b|\blavere lyd\b|\bturn (?:it|the volume) down\b")
#: How far "skru ned lyden" moves it, in percent.
VOLUME_STEP = 20


def volume_request(said: str) -> tuple[str, int] | None:
    """("set", percent) or ("step", ±percent) when this asks to change how loud the voice is."""
    words = " ".join(said.casefold().split())
    # RULE: a spoken volume is a change of volume, never a message
    if len(words) > SHORTEST_IS_SAFEST or _NOT.search(words):
        return None
    found = _VOLUME.search(words)
    if found:
        number = found.group(1)
        return "set", min(100, int(number) if number.isdigit() else _VOLUME_WORDS[number])
    if _LOUDER.search(words):
        return "step", VOLUME_STEP
    if _SOFTER.search(words):
        return "step", -VOLUME_STEP
    return None


def hang_up_request(said: str) -> bool:
    """Whether this asks the voice to put the microphone down."""
    clauses = [c for c in re.split(r"[,;!?.]", _FILLER.sub(" ", said.casefold())) if c.strip()]
    for clause in clauses:
        words = " ".join(clause.split())
        while (shorter := _ASKING.sub("", words)) != words:
            words = shorter
        words = _TRAILING.sub("", words)
        if not _NOT.search(words) and _HANG_UP.match(words):
            return True
    return False


def cancel_request(said: str) -> bool:
    """Whether this asks for the work under way to stop."""
    words = said.strip().strip(".!?,").casefold()
    return len(words) <= SHORTEST_IS_SAFEST and bool(_CANCEL.match(words))


def split_at_switch(transcript: str) -> tuple[str | None, str]:
    """The last line that asks to switch, and what was said after it.

    The page sends what was said since the last answer, one turn to a line. On
    2026-10-09 that was "Hei Hermes", "Bytt til Hermes" twice, and then a
    request: one message to the session he was leaving, and no switch.
    """
    lines = [line for line in transcript.splitlines() if line.strip()]
    # RULE: a switch said among other things still switches, and what follows goes to the new one
    for at in range(len(lines) - 1, -1, -1):
        if switch_request(lines[at]) is not None:
            return lines[at], "\n".join(lines[at + 1 :])
    return None, transcript


def greets_hermes(said: str) -> bool:
    """Whether this is "hei Hermes": what the voice itself suggests saying to reach Hermes."""
    whole = " ".join(said.casefold().split()).strip(" .!?")
    greeted = _GREETING.sub("", whole)
    # RULE: "hei Hermes" is a switch to Hermes, said alone or after a greeting
    return greeted != whole and bool(_TO_HERMES.fullmatch(greeted))


def switch_request(said: str) -> Target | str | None:
    """A target, a session name still to be matched, or None when this was not a switch."""
    # The last thing said is the wish: "not Hermes, back to the voice" is a switch to the voice.
    clauses = [c for c in re.split(r"[,.;!?]", _FILLER.sub(" ", said.casefold())) if c.strip()]
    words = " ".join(clauses[-1].split()) if clauses else ""
    if greets_hermes(said):
        return Target("hermes")
    while (shorter := _ASKING.sub("", words)) != words:
        words = shorter
    words = _TRAILING.sub("", words)
    # RULE: a long sentence that mentions talking to someone is not a switch
    if len(words) > SHORTEST_IS_SAFEST:
        return None
    found = _MOVE.match(words)
    if not found or _NOT.search(words):
        return None
    whom = found.group(1).strip()
    if _TO_VOICE.fullmatch(whom):
        return Target("voice")
    if _TO_HERMES.fullmatch(whom):
        return Target("hermes")
    # An unnamed session is "", for the bridge to ask which one.
    return "" if _ANY_SESSION.fullmatch(whom) else (_SESSION_WORD.sub("", whom).strip() or None)


# "Start en ny økt i voice-integration": a session started in the background
# and chosen at once. What comes after "i" or "in" is the project, as said.
_START = re.compile(
    r"^(?:start(?:e)?|lag(?:e)?|åpne|open|create)\s+(?:en\s+|a\s+)?(?:ny\s+|new\s+)?"
    r"(?:økt|økta|session)\s+(?:i|in)\s+(.+)$"
)


def start_request(said: str) -> str | None:
    """The project a new session should start in, or None when this was not asked."""
    clauses = [c for c in re.split(r"[,;!?]", _FILLER.sub(" ", said.casefold())) if c.strip()]
    words = " ".join(clauses[-1].split()).rstrip(".") if clauses else ""
    while (shorter := _ASKING.sub("", words)) != words:
        words = shorter
    if len(words) > SHORTEST_IS_SAFEST or _NOT.search(words):
        return None
    found = _START.match(words)
    return found.group(1).strip() if found else None


# "Lukk denne økta": stop a session the voice started. "Stopp" is left out,
# because it already means "avbryt" for whatever is under way.
_CLOSE = re.compile(
    r"^(?:lukk(?:e)?|avslutt(?:e)?|close|end)\s+(?:(?:denne|den|this|the)\s+)?"
    r"(?:økta|økten|session)(?:\s+(.+))?$"
)


def close_request(said: str) -> str | None:
    """The session to close, "" for the chosen one, or None when this was not asked."""
    clauses = [c for c in re.split(r"[,;!?]", _FILLER.sub(" ", said.casefold())) if c.strip()]
    words = " ".join(clauses[-1].split()).rstrip(".") if clauses else ""
    while (shorter := _ASKING.sub("", words)) != words:
        words = shorter
    if len(words) > SHORTEST_IS_SAFEST or _NOT.search(words):
        return None
    found = _CLOSE.match(words)
    return (found.group(1) or "").strip() if found else None


def matching(asked: str, running: list[dict[str, Any]]) -> list[str]:
    """The running sessions a spoken name or project could mean."""
    wanted = asked.casefold().replace(" ", "")
    exact = [s["name"] for s in running if str(s.get("name", "")).casefold().replace(" ", "") == wanted]
    if exact:
        return exact
    return [
        str(s["name"])
        for s in running
        if wanted in str(s.get("name", "")).casefold().replace(" ", "")
        or wanted in str(s.get("project", "")).casefold().rsplit("/", 1)[-1].replace(" ", "")
    ]
