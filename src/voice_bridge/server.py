"""The bridge: it serves the page, opens the session, and answers a delegation.

Three routes and no framework. A threaded server from the standard library is
enough for one person talking to their own machine, and it keeps the process
holding two keys small enough to read — which was
[ADR-VI-006]'s argument, given up in ADR-VI-018 and mostly kept anyway.

    GET  /                the page
    GET  /config          one phrase, in the session's language
    GET  /watch           every run's lifecycle, as server-sent events
    POST /spent           seconds of open microphone, booked against the month
    POST /where           coordinates the browser was allowed to give, kept in memory
    POST /noticed         what the voice plane did with what the page told it
    POST /session         the browser's WebRTC offer, exchanged for an answer
    POST /delegation      a transcript, answered with something to say aloud

The page never sees a key. It cannot: it is code handed to a browser.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from voice_bridge import budget, gateway, live, metrics, quick, sessions, target
from voice_bridge.budget import Ledger
from voice_bridge.policy import Capabilities, Refused
from voice_bridge.speech import say

PAGE = pathlib.Path(__file__).parent / "client" / "index.html"

#: How often a watcher is handed what has arrived.
WATCH_POLL_SECONDS = 0.4

#: What the page is allowed to report about the voice plane.
#:
#: The bridge hands an answer to the page and the page hands it to the voice,
#: and that second hop happens where the bridge cannot see it. So the answer
#: could arrive, be shown on screen, and never reach the voice at all — which
#: is exactly what it looked like from the outside, and there was no way to
#: tell that apart from a voice that heard it and chose to stay quiet.
#:
#: The list is closed rather than open because `notice` acts on some event
#: names: a page that could report `approval.request` could make the bridge
#: believe a permission question is open when none is.
PAGE_EVENTS = ("voice.told", "voice.unheard", "voice.lost")

#: How much of what the page reports is kept. It is a line of speech, not a log.
NOTICED_CHARACTERS = 400

#: What the gateway is told about this particular turn. A voice turn has to end
#: with something to say: dispatching work to a background subagent completes
#: the run immediately, and the real answer arrives later as a message nobody is
#: listening for. Heard from the person's side, that is the system saying "I am
#: starting it" and then never coming back.
TURN_INSTRUCTIONS = (
    "This request came in by voice. A person is listening and will answer by speaking. "
    # Heard aloud, verbatim: "CLOCK: 2026-09-17T12:38:47+02:00 DISK (/home):
    # Totalt 692G, Brukt 651G, Ledig 5,6G, 100% brukt MINNE: ..." — a wall of
    # command output, cut off mid-number by the spoken-length cap. The person's
    # own words: "why did you give me more information than I asked for".
    # Heard aloud: "ID 562691a8-f468-41cb-a58c-b938f929b14a". Nobody can hold
    # that, write it down or say it back, and nobody needs to.
    "Never say an identifier out loud — not a session, a run, a process or a "
    "file path. Nobody can hold one in their head and they are all on the screen. "
    # Asked "can you list them all? all nine", it answered that the names were
    # on the screen and it would not read them. A session's name is a word a
    # person says, not an identifier, and an explicit request beats a habit.
    "A session's name is not an identifier: say it. When the person asks you to "
    "list something or read it out, do, as briefly as it allows. "
    # Asked in passing whether questions were going to one place, it set up a
    # standing rule to forward everything there, started a second coding agent,
    # and began talking to one coding agent through another.
    "Decide who does each request as it arrives, and never set up a standing "
    "rule to send everything somewhere until told otherwise. Answer questions "
    "about this conversation yourself. Send work to a coding agent only when it "
    "needs a repository, a file or a command, and never reach one coding agent "
    "through another. "
    "Answer in one or two spoken sentences and stop. Round numbers and say the "
    "unit. Never pass on raw command output, a table, a heading, a bullet list, "
    "a path, a timestamp or a figure to more than two significant digits. If a "
    "tool gave you a wall of text, read it and say what it means. "
    # Heard on a walk, phone in a pocket: "the link is on the screen". There
    # was no link, and nobody was looking.
    "The person may not be looking at any screen: never send them to one "
    "instead of answering. Do not explain how you did it, do not offer "
    "next steps, and do not describe how the system works unless that is what "
    "was asked. "
    "Never ask them to reply with exact words, a quoted phrase, or a number from a list. "
    # Asked which voice model it was, it did not know, and spent 25 seconds
    # asking a coding session.
    "What they hear is the voice bridge: OpenAI's gpt-live-1 hears them and speaks "
    "your answer aloud. "
    # Heard on 2026-10-09: it said a location check was running, said it had
    # sent messages that the voice bridge had sent, and promised a message it
    # only sent when asked again.
    "You have no access to the person's phone, its GPS or their position; the voice bridge "
    "knows where they are, not you. Never say something is running or was sent unless a tool "
    "you called in this turn did it. Messages that reach a Claude session while the person "
    "talks to that session are sent by the voice bridge, not by you. When asked to send "
    "something, send it in this turn, not later. "
    "Do the work in this turn and answer with the result, except work you gave a session. "
    "Do not dispatch background subagents; run the tools yourself and wait for them. "
    "If it truly cannot be finished now, say in one sentence what you started and what is left. "
    # Everything below is here because the gateway asked, out loud, for one of
    # four numbered options containing file paths and hyphenated flags. Nobody
    # can say that back. A question a person cannot answer is worse than no
    # question: the work simply stops.
    # Five attempts at driving an interactive coding agent through its own
    # screen produced five "no visible answer"; the same question in print mode
    # answered correctly every time. ADR-VI-020.
    # Asked to list the Claude Code sessions, it started a brand-new `claude -p`
    # to go and look, asked for "Ja, kjør claude" first, and then said it had
    # used the session server it had never touched. ADR-VI-025.
    "To list the Claude Code sessions, or to ask, tell or read one that is already "
    "running, use the claude_voice tools: list_active_sessions, ask_active_session, "
    "read_session_output, session_recap. To say what every session is doing, call "
    "fleet_recap once rather than reading them one by one; to say what happened in a "
    "long session, call digest_session. Never start a new `claude -p` to find out "
    "about other sessions. Listing and reading change nothing, so do them without "
    "asking first. "
    # Asked only for their names, it offered to shut some of them down.
    "Never offer to stop, close or end a session; do it only when told to. "
    # A `claude -p` run is invisible: it is not in the person's tree, it sends
    # no news when it finishes, and it cannot ask for permission. ADR-VI-028.
    "For new work in a repository, reuse a session you started there before "
    "(list_sessions), or start one with create_session in that project (find it with "
    "list_projects with a word from its name), and give it the work with send_task. "
    "Do not wait for it to finish: "
    "say in one sentence what you started and where. The person hears from the "
    "session itself when it is done or needs permission. "
    "Never run `claude -p` or any other coding agent from the terminal. "
    "Never type into an interactive session on a screen and read the screen back, "
    "unless the person asked for a session they will use themselves. "
    # The person's own words, at the point they gave up: "why are you asking me
    # this, I do not know why I should choose this". Being asked to pick between
    # two ways of doing the same thing is not a question — it is the work,
    # handed back.
    "Do not ask the person to choose how you do something, or whether to try "
    "another way when one fails, or which of two sources to trust. Decide, do it, "
    "and say what you did in one sentence. Ask only about things that are theirs "
    "to decide: permission to change or run something, and what they actually want. "
    "When you need something from the person, ask one short question they can "
    "answer in a few spoken words. Never require exact wording, never read out a "
    "numbered list of options, never ask them to say a file path, a flag, a "
    "setting name or anything with punctuation in it. Offer at most two choices "
    "and name them in ordinary words. If you need a detail they cannot say, pick "
    "the sensible default, say which one you picked, and carry on."
)

#: The startup history is capped at 8,192 tokens across every message. Four
#: characters to the token is the usual rough measure, and this stays well under
#: it: being cut off mid-resume is worse than resuming less.
HISTORY_CHARACTERS = 24_000

#: How long a conversation is worth resuming. Come back an hour later and you
#: are starting something new, whatever the page still shows.
REMEMBER_FOR_SECONDS = 45 * 60

#: How many events the screen keeps. A run is a few dozen; a long session is
#: thousands, and nobody scrolls back that far.
WATCH_KEPT = 400


#: A phrase the last answer demanded back word for word. The gateway keeps
#: asking for these however often it is told not to, and a person walking down
#: the street cannot pronounce «Ja, kjør claude» on cue any more than they can
#: read out a session identifier.
DEMANDED = re.compile(
    r"(?:n\u00f8yaktig|eksakt|exactly|precisely|reply with|svar)"
    r"\s*[:\-]?\s*[\u00ab\"\u201c]"
    r"([^\u00bb\"\u201d\n]{2,60})[\u00bb\"\u201d]",
    re.IGNORECASE,
)


def demanded_phrase(spoken: str) -> str | None:
    """The words an answer insisted on hearing back, if it insisted on any."""
    found = DEMANDED.search(spoken)
    return found.group(1).strip() if found else None


def still_running(payload: object) -> bool:
    """Whether there is more to come, so somebody should keep waiting."""
    return isinstance(payload, dict) and payload.get("status") in ("queued", "running")


#: How a delegation becomes work. The transcript is the only thing the model
#: gives us, so the gateway is asked to plan against it — which is the whole
#: argument of ADR-VI-001, arriving here as one HTTP call.
#:
#: The room is also the gateway's memory, and a room remembers how things were
#: done — including badly. A hundred turns of driving a coding agent through its
#: terminal outweighed both the skill and the instruction telling it not to, and
#: it kept reaching for a session that no longer existed. Changing the room is
#: how you stop paying for a habit.
#:
#: It is named for the orchestrator rather than for the voice, because that is
#: whose conversation it is. The voice holds a few turns and forgets them; this
#: is where the thinking and the memory live.
ROOM = os.environ.get("VOICE_BRIDGE_ROOM", "orchestrator")


def as_said(transcript: str) -> str:
    """What was heard, as the separate things it was, not one run-on line.

    The page sends its turns one to a line. Flattening them into a single
    sentence produced requests like "can we do something meanwhile yes run
    claude", which reads as one confused instruction rather than a question and
    then an answer to a different one.
    """
    # RULE: separate things said stay separate when they are sent on
    said = [line.strip() for line in transcript.splitlines() if line.strip()]
    return "\n".join(said)


def notice(server: Bridge, event: dict[str, Any]) -> None:
    """Keep an event for whoever is watching, and no more than a screenful."""
    # A run can ask for permission long after we stopped waiting for it, so the
    # question is caught here rather than by whoever happened to be polling.
    # RULE: a permission question is noticed however late it arrives
    if str(event.get("event", "")).startswith("approval.request"):
        server.awaiting = str(event.get("run_id") or server.awaiting or "")
    with server.watching_lock:
        server.watching.append(event)
        del server.watching[:-WATCH_KEPT]


def resolve_pending(bridge: Bridge, choice: str) -> str:
    """Answer the permission question the room is waiting on."""
    run_id, bridge.awaiting = bridge.awaiting, None
    if not run_id:
        return "There is nothing waiting for permission."
    spoken = gateway.call(
        "approval_resolve", {"run_id": run_id, "choice": choice}, bridge.gateway_url, bridge.capabilities
    )
    if choice == "deny":
        return spoken
    finished = gateway.wait_for(run_id, bridge.gateway_url)
    if isinstance(finished, dict) and finished.get("status") == "waiting_for_approval":
        bridge.awaiting = run_id
    return say("run_status", finished)


def said_for_them(bridge: Bridge, transcript: str) -> str:
    """Substitute the phrase an answer demanded, when the person simply agreed."""
    if bridge.demanded and live.answer_to_a_question(transcript) == "once":
        # RULE: a phrase the gateway demanded is said for the person, not by them
        transcript, bridge.demanded = bridge.demanded, None
    return transcript


def answer_session(bridge: Bridge, choice: str, approval_id: str | None = None) -> str:
    """Answer a request a Claude Code session is waiting on, through claude-voice."""
    if approval_id is None:
        # RULE: a spoken answer settles a coding session only when one request waits
        if len(bridge.asked) > 1:
            return f"{len(bridge.asked)} requests are waiting. Answer each with its own button on the screen."
        approval_id = next(iter(bridge.asked), None)
    if approval_id is None or approval_id not in bridge.asked or bridge.sessions is None:
        return "There is nothing waiting for permission."
    heard = bridge.asked.pop(approval_id)
    try:
        bridge.sessions.call("approve" if choice == "once" else "deny", {"approval_id": approval_id})
    except Refused:
        return "That request is no longer waiting."
    except OSError:
        bridge.asked[approval_id] = heard
        return "I could not reach the coding sessions."
    return "Allowed, once." if choice == "once" else "Refused."


def pending_answer(bridge: Bridge, transcript: str) -> str | None:
    """Resolve a waiting permission question, if this was an answer to one."""
    if not bridge.awaiting and not bridge.asked:
        return None
    answered = live.answer_to_a_question(transcript)
    # RULE: only a word that is plainly yes or no answers a permission question
    if answered is None:
        return None
    if bridge.awaiting:
        return resolve_pending(bridge, answered)
    # RULE: a plain yes or no answers the coding session that asked
    return answer_session(bridge, answered)


def answered_here(bridge: Bridge, transcript: str) -> tuple[str | None, str]:
    """Whatever the bridge can settle without the gateway, and what is left to send."""
    # RULE: a question the bridge can answer never travels further
    immediate = quick.answer(bridge, transcript)
    if immediate is not None:
        return immediate, transcript
    transcript = said_for_them(bridge, transcript)
    return pending_answer(bridge, transcript), transcript


#: What a turn hears while nothing is forwarded. ADR-VI-026.
VOICE_ALONE = (
    "Nothing was passed on: the person chose to talk to you alone. Answer them yourself, "
    "briefly, from what you know. If it needs a coding agent, say once that they can say "
    "snakk med Hermes, or name a session."
)

#: How much of what was missed is said word for word when the microphone is
#: taken again. The rest is counted, and left on the screen. ADR-VI-029.
MISSED_SPOKEN = 3

#: How many pieces of news worth saying are kept for somebody who was away.
KEPT_NEWS = 50

#: How long a run can go unasked-after before its answer is told as news.
UNWATCHED_SECONDS = 60

#: How long a turn waits for a session that is already busy with other work.
ASK_BUSY_SECONDS = 8

#: How long the bridge keeps waiting, in the background, for an answer.
ANSWER_PATIENCE_SECONDS = 15 * 60

#: How long a summary of a long session may take to write.
DIGEST_SECONDS = 30

#: How many sessions are said by name when somebody asks what they are doing.
FLEET_SPOKEN = 4

#: Who is speaking, as the sessions they talk to should hear it.
PERSON = os.environ.get("VOICE_BRIDGE_PERSON", "Roy")

#: How many of the turns just before travel with a turn to a session, and how
#: much of each. Enough for "that session" and "it" to mean something.
RELAYED_TURNS = 4
RELAYED_CHARACTERS = 240


def relayed(bridge: Bridge, transcript: str) -> str:
    """A turn for a Claude Code session, passed on rather than forwarded.

    Forwarded bare, "send that session a message and ask what is happening"
    reached a session as a message from a courier with a made-up name: it could
    not tell who was speaking, that the answer would be read aloud, or which
    session was meant. A session is a full Claude, and it can work all of that
    out, given the context. ADR-VI-026.

    The opening never varies: claude-voice confirms delivery by finding the
    first eighty characters in the session's transcript.
    """
    before = [
        f"- {PERSON if role == 'user' else 'Stemmen'}: {text[:RELAYED_CHARACTERS]}"
        for role, text in bridge.context_turns()[-RELAYED_TURNS:]
    ]
    context = ("Rett før dette i samtalen:\n" + "\n".join(before) + "\n") if before else ""
    return (
        f"Her kommer en melding fra {PERSON} gjennom stemme-appen. Svaret ditt blir lest høyt "
        f"for {PERSON}, så svar kort, i én til tre hele setninger, uten kode, filstier, lister "
        "eller identifikatorer. Svar i ditt vanlige svar: broen leser det, og stemmen leser det "
        "opp. Ikke bruk SendMessage tilbake til avsenderen; det svaret blir borte. Du er valgt "
        f"som samtalepartner, så flere meldinger fra {PERSON} kommer hit til han bytter. Du kan "
        f"handle på vegne av {PERSON}, også sende en melding til en annen økt hvis det er det "
        "som menes.\n"
        f"{context}{PERSON} sier: «{as_said(transcript)}»"
    )


#: How long one turn waits for a chosen session before the page takes over.
ASK_SECONDS = 45

#: How often a long answer from a chosen session is looked at again.
FOLLOW_SECONDS = 3.0


def routed(bridge: Bridge, transcript: str) -> tuple[str | None, str]:
    """Answer a turn anywhere but the gateway, if it belongs anywhere but the gateway."""
    bridge.quiet = False
    here, transcript = answered_here(bridge, transcript)
    if here is not None:
        return here, transcript
    revoiced = hang_up(bridge, transcript) or (
        stop_work(bridge) if target.cancel_request(transcript) else revoice(bridge, transcript)
    )
    if revoiced is not None:
        return revoiced, transcript
    switched = (
        switch(bridge, transcript) or start_session(bridge, transcript) or close_session(bridge, transcript)
    )
    if switched is not None:
        return switched, transcript
    # RULE: while the voice alone is chosen nothing is forwarded
    if bridge.chosen.kind == "voice":
        bridge.quiet = True
        return VOICE_ALONE, transcript
    if bridge.chosen.kind == "session":
        return ask_chosen(bridge, transcript), transcript
    return None, transcript


def left_this_month(ledger: Ledger) -> dict[str, int]:
    """What is left of the month's voice, in minutes: a dollar figure read as an account balance."""
    return {
        # Rounded to the whole minute: 19.95 / 0.05 is 398.999… in floating point.
        "remaining_minutes": int(round(ledger.remaining_usd() / budget.USD_PER_MINUTE, 6)),
        "ceiling_minutes": int(budget.ceiling_usd() / budget.USD_PER_MINUTE),
    }


def hang_up(bridge: Bridge, transcript: str) -> str | None:
    """Put the microphone down, if that was asked: the page does it once this is said."""
    if not target.hang_up_request(transcript):
        return None
    # Nothing more is paid for once the microphone is down.
    bridge.hanging_up = True
    return "Greit, jeg legger på."


def stop_work(bridge: Bridge) -> str:
    """Stop what is under way: the gateway's runs, and answers still owed by busy sessions."""
    said = []
    for run_id in sorted(bridge.open_runs):
        try:
            gateway.call("run_stop", {"run_id": run_id}, bridge.gateway_url, bridge.capabilities)
        except (OSError, Refused):
            continue
        bridge.open_runs.discard(run_id)
        said.append("Stopped what Hermes was doing.")
    owed = sorted(bridge.answers_awaited)
    for name in owed:
        # Its answer, when it comes, is no longer wanted.
        bridge.dropped.add(name)
        bridge.answers_awaited.pop(name)
    chosen = [bridge.chosen.name] if bridge.chosen.kind == "session" else []
    said.extend(_stop_session(bridge, name) for name in dict.fromkeys([*owed, *chosen]))
    return " ".join(dict.fromkeys(s for s in said if s)) or "There was nothing under way to stop."


def _stop_session(bridge: Bridge, name: str) -> str:
    """Stop one session's current turn through claude-voice, or say honestly that it cannot be."""
    if bridge.sessions is None:
        return ""
    try:
        got = bridge.sessions.call("cancel", {"session_id": name})
    except (OSError, Refused):
        return f"I could not reach {name} to stop it."
    if got.get("status") == "interrupted":
        return f"Stopped {name}."
    if got.get("status") == "not_supported":
        # A terminal session: Ctrl-C would end it outright, and nothing can type into it.
        return f"{name} cannot be stopped from here; it has to be stopped at its own screen."
    return ""


def revoice(bridge: Bridge, transcript: str) -> str | None:
    """List the voices, or change the one the chosen target speaks with."""
    asked = target.voice_request(transcript)
    if asked is None:
        return None
    if asked == "list":
        named = ", ".join(live.VOICES)
        return f"The voices are {named}. {_opening(bridge.chosen.said())} speaks as {bridge.voice_now()}."
    if not bridge.revoice(bridge.chosen.kind, asked):
        return f"There is no voice called {asked}."
    return f"{_opening(bridge.chosen.said())} will speak as {asked} from now on."


def _opening(words: str) -> str:
    """Words that start a sentence, with the capital a sentence starts with."""
    return words[:1].upper() + words[1:]


def switch(bridge: Bridge, transcript: str) -> str | None:
    """Change who turns go to, if that is what was asked."""
    asked = target.switch_request(transcript)
    if asked is None:
        return None
    if isinstance(asked, target.Target):
        bridge.choose(asked)
        return f"You are talking to {asked.said()} now."
    if not asked:
        names = [str(s.get("name")) for s in bridge.running()][:3]
        return "Which session? " + (f"For example {', '.join(names)}." if names else "None is running now.")
    found = target.matching(asked, bridge.running())
    # RULE: a name is switched to only when it matches exactly one session
    if len(found) != 1:
        if not found:
            return f"No running session is called {asked}."
        return f"{asked} could be {', '.join(found)}. Which one?"
    bridge.choose(target.Target("session", found[0]))
    return f"You are talking to {found[0]} now."


#: How long claude-voice may take to start a session and see it running.
START_SECONDS = 20.0


def start_session(bridge: Bridge, transcript: str) -> str | None:
    """Start a session in the background, if that was asked, and choose it at once."""
    asked = target.start_request(transcript)
    if asked is None:
        return None
    if bridge.sessions is None:
        return "I cannot start a session: the coding sessions cannot be reached."
    # Folders are written with hyphens and said with spaces.
    project = "-".join(asked.split())
    try:
        started = bridge.sessions.call("start_active_session", {"project": project}, waits=START_SECONDS)
    except (OSError, Refused) as failure:
        return f"I could not start a session in {project}: {failure}"
    name = str(started.get("name") or "")
    if not name:
        return f"I could not start a session in {project}."
    bridge.choose(target.Target("session", name))
    return f"I started {name} in {project}, and you are talking to it now."


def close_session(bridge: Bridge, transcript: str) -> str | None:
    """Stop a session the voice started, if that was asked, and hand the talk back to the voice."""
    asked = target.close_request(transcript)
    if asked is None:
        return None
    name = asked or (bridge.chosen.name if bridge.chosen.kind == "session" else "")
    if not name:
        return "Which session should I close?"
    if bridge.sessions is None:
        return "I cannot close a session: the coding sessions cannot be reached."
    try:
        stopped = bridge.sessions.call("stop_active_session", {"name": name})
    except (OSError, Refused) as failure:
        return f"I could not close {name}: {failure}"
    return _closed(bridge, name, str(stopped.get("status") or ""))


def _closed(bridge: Bridge, name: str, status: str) -> str:
    """What to say once claude-voice has answered a close, and who is talked to after."""
    if status == "not_started_here":
        # claude-voice keeps the record, and refuses anything it did not start.
        return f"I only close sessions I started myself. {name} has to be closed where it was opened."
    if status != "stopped":
        return f"{name} is not running."
    if bridge.chosen == target.Target("session", name):
        bridge.choose(target.Target(kind="voice"))
        return f"I closed {name}. You are talking to the voice alone now."
    return f"I closed {name}."


#: How long claude-voice may take to answer from a busy session's transcript.
SIDE_SECONDS = 20.0

# Words a question starts with. "kan du …" and "vil du …" are left out: they
# are as often requests to do something as questions.
_QUESTION = re.compile(
    r"^(?:hva|hvor|hvordan|hvorfor|hvem|når|hvilke|hvilken|har|er|"
    r"what|where|how|why|who|when|which|has|have|is|are|did|does)\b"
)


def is_question(transcript: str) -> bool:
    """Whether what was said asks something, rather than asking for something to be done."""
    said = " ".join(transcript.casefold().split())
    return said.endswith("?") or bool(_QUESTION.match(said))


def side_answer(bridge: Bridge, name: str, transcript: str) -> str | None:
    """A question to a busy session, answered at once from what it has written.

    Like Claude Code's /btw, asked for by Roy on 2026-10-09: the session is not
    interrupted and the question never reaches it, so the person does not wait
    for the work to end.
    """
    language = live.LANGUAGE_NAMES.get(live.LANGUAGE, live.LANGUAGE)
    try:
        got = bridge.sessions.call(  # type: ignore[union-attr]  # checked by the caller
            "side_question",
            {"session": name, "question": transcript, "language": language},
            waits=SIDE_SECONDS,
        )
    except (OSError, Refused):
        return None
    answer = answer_in({"reply": str(got.get("answer") or "")})
    return f"Fra det {name} har skrevet: {answer}" if answer else None


def ask_chosen(bridge: Bridge, transcript: str) -> str:
    """Put a turn to the chosen session, as if it were the only one there is."""
    chosen = bridge.chosen
    if bridge.sessions is None:
        return "I cannot reach the coding sessions."
    # A session busy with other work reads nothing until it is done; waiting
    # the full time only fills the silence with "still working".
    busy = {s.get("name"): s.get("status") for s in bridge.running()}.get(chosen.name) in ("busy", "shell")
    if busy and is_question(transcript):
        aside = side_answer(bridge, chosen.name, transcript)
        if aside:
            return aside
        # No quick answer to be had: the question goes to the session, and its
        # answer comes as news when it is free.
    wait = ASK_BUSY_SECONDS if busy else ASK_SECONDS
    try:
        got = bridge.sessions.call(
            "ask_active_session",
            # RULE: a turn to a session says who is speaking and that the answer is read aloud
            {"session": chosen.name, "message": relayed(bridge, transcript), "wait_seconds": wait},
            # The tool itself waits; the call has to outlast it.
            waits=wait,
        )
    except Refused as refusal:
        return f"{chosen.name} could not be reached: {refusal}"
    except OSError:
        return "I cannot reach the coding sessions."
    return _after_asking(bridge, chosen, got, transcript)


#: The most of a session's answer that is read aloud. The rest is on its screen.
SPOKEN_ANSWER = 400

_NOT_SPOKEN = re.compile(r"^\s*(?:\|.*\||```.*|#+\s.*)$", re.MULTILINE)


def answer_in(got: dict[str, Any], *, first: bool = False) -> str:
    """The part of what a session wrote that answers the turn, fit to be heard.

    A session busy with other work when the turn arrived wrote all of that too,
    and it all came back as the reply: two thousand characters with a table in
    them, when the answer was the last sentence. So only the last thing it wrote
    is spoken, without tables, code or headings, and only so much of it.
    """
    written = [str(t.get("text", "")) for t in got.get("turns") or [] if t.get("role") == "assistant"]
    last = written[0 if first else -1] if written else str(got.get("reply") or "")
    plain = _NOT_SPOKEN.sub("", last).replace("**", "").replace("`", "")
    plain = " ".join(plain.split())
    # claude-voice marks a turn it clipped, and ends it in an ellipsis.
    if len(plain) <= SPOKEN_ANSWER and not plain.endswith("…"):
        return plain
    return _whole_sentences(plain.rstrip("…")[:SPOKEN_ANSWER])


def _ended(line: str) -> str:
    """A line with exactly one mark at the end, whatever it came with."""
    line = line.strip().rstrip("…").strip()
    return line if line.endswith((".", "?", "!")) else f"{line}."


def _whole_sentences(text: str) -> str:
    """The text up to its last finished sentence: a half sentence read aloud is noise."""
    ends = [text.rfind(mark) for mark in (". ", "? ", "! ")]
    end = max(ends)
    if text.endswith((".", "?", "!")) and end < len(text) - 1:
        return text
    return text[: end + 1] if end > 0 else text.rsplit(" ", 1)[0]


def _moved(bridge: Bridge, chosen: target.Target, moved: dict[str, Any]) -> str:
    """Follow a conversation that carried on in another session, or give up on it."""
    # The old window of a continued conversation takes messages and never answers.
    if not moved.get("name"):
        bridge.choose(target.Target("voice"))
        return f"{chosen.name} has moved somewhere I cannot see, so you are talking to me again."
    bridge.choose(target.Target("session", str(moved["name"])))
    return f"{chosen.name} carried on as {moved['name']}, so you are talking to that now. Say it again."


def _waiting(chosen: target.Target, got: dict[str, Any]) -> str:
    """What to say about a session held up at its own screen, or nothing."""
    status = got.get("status")
    if status == "needs_choice":
        # A box stops the session until somebody answers it at the keyboard;
        # anything said meanwhile only queues behind it.
        asked = got.get("question") or {}
        options = [
            str(o.get("label", o)) if isinstance(o, dict) else str(o) for o in asked.get("options") or []
        ]
        choices = f" The choices are {' or '.join(options)}." if options else ""
        return f"{chosen.name} is waiting for a choice at its screen: {asked.get('text', '')}{choices}"
    if status == "needs_input":
        return f"{chosen.name} is waiting for somebody at its own screen."
    if status == "not_received":
        return f"{chosen.name} did not get that. It may be waiting for somebody at its own screen."
    return ""


def _after_asking(bridge: Bridge, chosen: target.Target, got: dict[str, Any], transcript: str) -> str:
    """What to say about one answer from a chosen session."""
    status = got.get("status")
    if status == "session_ended" or got.get("session_ended"):
        # RULE: a session that ended hands the conversation back to the voice
        bridge.choose(target.Target("voice"))
        return f"{chosen.name} has ended, so you are talking to me again."
    if status == "moved":
        return _moved(bridge, chosen, got.get("moved_to") or {})
    waiting = _waiting(chosen, got)
    if waiting:
        return waiting
    reply = answer_in(got)
    if status == "still_working":
        # Not quoted: what a busy session wrote last is not an answer to this.
        # The bridge waits for the answer itself and tells it as news, so the
        # page is not left polling and the voice does not fill the wait.
        return bridge.await_answer(chosen.name, int(got.get("next_after", 0)), said=transcript)
    return reply or f"{chosen.name} said nothing."


#: How much of what was said is looked for in the session's transcript: the
#: start is enough to know the question, and long turns may be shown cut.
QUESTION_CHARACTERS = 40


def _slipped_in(text: str) -> bool:
    """Whether a turn is a note added while the session was working, not a new request."""
    return text.lstrip().startswith("<system-reminder")


def _reply_to(read: dict[str, Any], said: str) -> tuple[str, bool]:
    """The session's reply to the turn that carried `said`, and whether that turn is over.

    A busy session reads the question only when it is free, and writes other
    things meanwhile, for other people and other prompts. On 2026-10-09 one of
    those, "Venter.", was read aloud as the answer, and the real answer lost.
    So only what it wrote after the question arrived, and before the next thing
    it was asked, counts.
    """
    wanted = " ".join(said.casefold().split())[:QUESTION_CHARACTERS]
    turns = list(read.get("turns") or [])
    asked = next(
        (
            i
            for i, turn in enumerate(turns)
            if turn.get("role") == "user" and wanted in " ".join(str(turn.get("text", "")).casefold().split())
        ),
        None,
    )
    if asked is None:
        # RULE: a busy session's answer is only what it wrote after reading the question
        return "", False
    written: list[dict[str, Any]] = []
    for turn in turns[asked + 1 :]:
        # A note slipped in while the session works is not the next thing it
        # was asked: on 2026-10-09 one ended a reply before it was written.
        if turn.get("role") == "user" and not _slipped_in(str(turn.get("text", ""))):
            return (answer_in({"turns": written[-1:]}) if written else ""), True
        if turn.get("role") == "assistant" and str(turn.get("text", "")).strip():
            written.append(turn)
    return (answer_in({"turns": written[-1:]}) if written else ""), False


def _follow_reply(bridge: Bridge, following: str, patience: float, said: str) -> tuple[str, bool]:
    """Wait for the session's reply to what was said, and nothing written before or after it."""
    _, after, name = following.split(":", 2)
    deadline = time.monotonic() + patience
    while time.monotonic() < deadline:
        try:
            read = (
                bridge.sessions.call("read_session_output", {"session": name, "after": int(after)})
                if bridge.sessions
                else {}
            )
            status = read.get("status") or {s.get("name"): s.get("status") for s in bridge.running()}.get(
                name
            )
        except (OSError, Refused):
            return "", False
        reply, over = _reply_to(read, as_said(said))
        if status is None:
            bridge.choose(target.Target(kind="voice"))
            return f"{reply} {name} has ended, so you are talking to me again.".strip(), True
        if reply and (over or status in ("idle", "waiting")):
            return reply, True
        time.sleep(FOLLOW_SECONDS)
    return "", False


def follow_chosen(bridge: Bridge, following: str, patience: float, said: str = "") -> tuple[str, bool]:
    """Wait for a chosen session to finish an answer, and say what it wrote."""
    if said:
        return _follow_reply(bridge, following, patience, said)
    _, after, name = following.split(":", 2)
    deadline = time.monotonic() + patience
    while True:
        try:
            asked = {"session": name, "after": int(after)}
            read = bridge.sessions.call("read_session_output", asked) if bridge.sessions else {}
            listed = {s.get("name"): s.get("status") for s in bridge.running()}
            status = read.get("status") or listed.get(name)
        except (OSError, Refused):
            return "", False
        # The first thing written after the question is the answer. A session
        # that never goes idle, because somebody is working with it at the same
        # time, otherwise had its answer held back for good.
        written = [answer_in(read, first=True)] if answer_in(read, first=True) else []
        if written and status is not None:
            return written[0], True
        if status is None:
            bridge.choose(target.Target("voice"))
            return " ".join([*written, f"{name} has ended, so you are talking to me again."]).strip(), True
        if status in ("idle", "waiting"):
            return " ".join(written).strip() or f"{name} is done.", True
        if time.monotonic() >= deadline:
            return "", False
        time.sleep(FOLLOW_SECONDS)


#: What the transcriber writes for a sound that is not a word: "[clear throat]",
#: "[latter]". It once reached a session as the start of what Roy said.
NOISE = re.compile(r"\[[^\]]{0,40}\]")


def without_noises(transcript: str) -> str:
    """What was said, without the sounds the transcriber marked."""
    # RULE: a sound the transcriber marked is not something the person said
    return NOISE.sub("", transcript)


def answer_delegation(  # noqa: PLR0913 — a turn needs all six, and bundling them hides what it uses
    transcript: str,
    url: str,
    *,
    capabilities: Capabilities | None = None,
    patience: float = gateway.PATIENCE_SECONDS,
    watcher: Callable[[str, str], None] | None = None,
    bridge: Bridge | None = None,
) -> str:
    """Turn what was heard into something to say back."""
    transcript = without_noises(transcript)
    if not transcript.strip():
        return "I did not catch that."
    # A question that is waiting takes precedence over a new request: "yes" is
    # an answer to it, not a thing to go and do.
    if bridge is not None:
        here, transcript = routed(bridge, transcript)
        if here is not None:
            return here
    arguments: dict[str, Any] = {
        "agent": "hermes-agent",
        "instruction": as_said(transcript),
        "room": ROOM,
    }
    (capabilities or Capabilities()).permit("agent_task", arguments)
    planned = gateway.plan("agent_task", arguments, url)
    # RULE: a voice turn asks the gateway to finish inside it
    carrying: dict[str, Any] = {"instructions": TURN_INSTRUCTIONS}
    if bridge is not None:
        # RULE: a request carries the conversation it came out of
        carrying["conversation_history"] = bridge.context()
    asking = replace(planned, body={**(planned.body or {}), **carrying})
    started = gateway.send(asking)
    run_id = started.get("run_id") if isinstance(started, dict) else None
    if not run_id:
        return say("agent_task", started)
    if watcher is not None:
        watcher(str(run_id), as_said(transcript))
    # RULE: a delegation waits for the work rather than reading back a receipt
    finished = gateway.wait_for(str(run_id), url, patience)
    if bridge is not None:
        if isinstance(finished, dict) and finished.get("status") == "waiting_for_approval":
            bridge.awaiting = str(run_id)
        # RULE: a turn is finished only when the run behind it is
        bridge.following = str(run_id) if still_running(finished) else None
    spoken = say("run_status", finished)
    if bridge is not None:
        bridge.demanded = demanded_phrase(str((finished or {}).get("output") or spoken))
    return spoken


def keep_waiting(
    run_id: str, url: str, patience: float = gateway.PATIENCE_SECONDS, bridge: Bridge | None = None
) -> tuple[str, bool]:
    """Wait another stretch for a run, and say what to speak and whether to stop."""
    if run_id.startswith("claude:") and bridge is not None:
        return follow_chosen(bridge, run_id, patience)
    seen = gateway.wait_for(run_id, url, patience)
    return say("run_status", seen), not still_running(seen)


class _Handler(BaseHTTPRequestHandler):
    """The three routes, and nothing else reachable."""

    server: Bridge

    def log_message(self, *_args: object) -> None:
        """Say nothing: the default writes every request to stderr."""

    def _send(self, status: int, payload: dict[str, Any] | None = None, page: bytes = b"") -> None:
        body = page or json.dumps(payload or {}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8" if page else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) or b"{}"
        loaded = json.loads(raw)
        return loaded if isinstance(loaded, dict) else {}

    def do_GET(self) -> None:
        """Serve the page, and only the page."""
        if self.path in ("/", "/index.html"):
            self._send(200, page=PAGE.read_bytes())
        elif self.path == "/watch":
            self._stream()
        elif self.path == "/target":
            self._send(200, self._who())
        elif self.path == "/health":
            self._send(200, self.server.health())
        elif self.path == "/usage":
            self._send(200, self.server.usage())
        elif self.path == "/config":
            # The page needs one phrase in the session's language and nothing
            # else. It is never given a key, a model name or a gateway address.
            self._send(200, {"holding": live.holding()})
        else:
            self._send(404, {"error": "no such path"})

    def _stream(self) -> None:
        """Send what has happened, then everything that happens next."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        sent = 0
        try:
            while True:
                with self.server.watching_lock:
                    pending = self.server.watching[sent:]
                    sent = len(self.server.watching)
                for event in pending:
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                if not pending:
                    self.wfile.write(b": still here\n\n")
                self.wfile.flush()
                time.sleep(WATCH_POLL_SECONDS)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _kept(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """The two routes that only report what the page did with what it was given."""
        if path == "/timing":
            # How long each stage of one turn took, as the page saw it: the
            # bridge's answer, the voice taking it, and its first words after;
            # and for a session, how long from the button to a voice that listens.
            for stage in ("bridge", "acknowledged", "first_words", "opened"):
                if isinstance(body.get(f"{stage}_ms"), (int, float)):
                    self.server.store.record("stage", stage, ms=float(body[f"{stage}_ms"]))
            return {}
        self.server.heard_up_to(int(body.get("seq", 0)))
        return {}

    def _small(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """The routes that only put something away and answer briefly."""
        if path in ("/heard", "/timing"):
            return self._kept(path, body)
        if path == "/noticed":
            reported = str(body.get("event", ""))
            # RULE: the page may only report events in its own name
            if reported not in PAGE_EVENTS:
                refusal = f"{reported or 'that'} is not the page's to report"
                raise Refused(refusal)
            notice(
                self.server,
                {"event": reported, "detail": str(body.get("detail", ""))[:NOTICED_CHARACTERS]},
            )
            return {}
        if path == "/spent":
            # RULE: an open microphone is booked while it is open
            self.server.ledger.record(float(body.get("seconds", 0)))
            # Kept by day too, for the chart of voice use over time.
            self.server.store.record("voice", "open", ms=float(body.get("seconds", 0)) * 1000)
            return left_this_month(self.server.ledger)
        if path == "/where":
            # RULE: a position is held in memory and written nowhere
            self.server.placed = quick.place_of(
                float(body.get("latitude", 0)), float(body.get("longitude", 0))
            )
            if not self.server.placed:
                return {"placed": None}
            # The page passes this on to the voice, which otherwise holds no
            # position at all and says so while the page displays one.
            return {"placed": self.server.placed, "known": live.known_place(self.server.placed)}
        self.server.remember(str(body.get("who", "")), str(body.get("text", "")))
        return {}

    def _who(self) -> dict[str, Any]:
        """Who turns go to now, and who else they could go to, and what each is doing."""
        doing = {s["name"]: s.get("doing", "") for s in self.server.fleet()}
        return {
            "chosen": self.server.chosen.as_json(),
            "sessions": [
                {
                    **{key: s.get(key) for key in ("name", "project", "status", "kind")},
                    "doing": doing.get(str(s.get("name")), ""),
                }
                for s in self.server.running()
            ],
            "tree": self.server.tree(),
            "voice": self.server.voice_now(),
            "steer": target.steer(self.server.chosen),
            "voices": self.server.voices,
            "available": list(live.VOICES),
        }

    def _revoice(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Pick the voice one kind of target speaks with, from the page."""
        kind = str(body.get("kind", ""))
        if kind not in target.KINDS:
            return 400, {"error": "a voice belongs to the voice, hermes or a session"}
        if not self.server.revoice(kind, str(body.get("voice", ""))):
            refusal = f"{body.get('voice') or 'that'} is not a voice the service offers"
            raise Refused(refusal)
        return 200, {"voices": self.server.voices, "voice": self.server.voice_now()}

    def _choose(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Set who turns go to, from a tap on the page."""
        kind = str(body.get("kind", ""))
        if kind not in target.KINDS:
            return 400, {"error": "choose the voice, hermes or a session"}
        chosen = target.Target(kind, str(body.get("name", "")) if kind == "session" else "")
        # RULE: a session is chosen from the page only if it is running
        if kind == "session" and chosen.name not in [s.get("name") for s in self.server.running()]:
            refusal = f"{chosen.name or 'that session'} is not running"
            raise Refused(refusal)
        self.server.choose(chosen)
        return 200, {"chosen": chosen.as_json(), "said": f"You are talking to {chosen.said()} now."}

    def _approval(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Answer a permission question from a button, with once or deny and nothing else."""
        choice = str(body.get("choice", ""))
        if choice not in ("once", "deny"):
            return 400, {"error": "a permission is answered once or deny"}
        if "approval_id" not in body:
            return 200, {"content": resolve_pending(self.server, choice)}
        asked = str(body["approval_id"])
        # RULE: a button answers only a request the bridge was told about
        if asked not in self.server.asked:
            refusal = "that request was never asked here"
            raise Refused(refusal)
        return 200, {"content": answer_session(self.server, choice, asked)}

    def do_POST(self) -> None:
        """Open a session, or answer a delegation."""
        try:
            body = self._read()
            if self.path == "/session":
                sdp = live.open_session(
                    str(body.get("sdp", "")),
                    self.server.ledger,
                    history=self.server.recent(),
                    # RULE: a session opens in the voice of the chosen target
                    voice=self.server.voice_now(),
                    # RULE: a chosen session hears everything that is said
                    steer=target.steer(self.server.chosen),
                    about=live.whereabouts(str(body.get("client") or "")),
                )
                self._send(
                    200,
                    {
                        "sdp": sdp,
                        "resumed": len(self.server.recent()),
                        "voice": self.server.voice_now(),
                        "steer": target.steer(self.server.chosen),
                        # RULE: news that was not heard is said when the microphone is taken again
                        "missed": self.server.missed(),
                    },
                )
            elif self.path == "/approval":
                self._send(*self._approval(body))
            elif self.path == "/target":
                self._send(*self._choose(body))
            elif self.path == "/voice":
                self._send(*self._revoice(body))
            elif self.path in ("/where", "/turn", "/spent", "/noticed", "/heard", "/timing"):
                self._send(200, self._small(self.path, body))
            elif self.path == "/delegation":
                self.server.following = None
                self.server.quiet = False
                # RULE: every spoken turn is traced and measured
                with (
                    metrics.tracing(metrics.new_trace()),
                    metrics.measured(self.server.store, "turn", self.server.chosen.kind) as outcome,
                ):
                    spoken = answer_delegation(
                        str(body.get("transcript", "")),
                        self.server.gateway_url,
                        capabilities=self.server.capabilities,
                        watcher=self.server.follow,
                        bridge=self.server,
                    )
                    outcome["detail"] = (
                        "quiet" if self.server.quiet else "following" if self.server.following else "answered"
                    )
                self._send(
                    200,
                    {
                        "content": spoken,
                        "run_id": self.server.following,
                        "finished": self.server.following is None,
                        # Something for the voice to know rather than to say.
                        "quiet": self.server.quiet,
                        "hang_up": self.server.hanging_up,
                    },
                )
                self.server.hanging_up = False
            elif self.path == "/run":
                run_id = str(body.get("run_id", ""))
                self.server.polled[run_id] = time.monotonic()
                spoken, done = keep_waiting(run_id, self.server.gateway_url, bridge=self.server)
                self.server.polled[run_id] = time.monotonic()
                self._send(200, {"content": spoken, "finished": done})
            else:
                self._send(404, {"error": "no such path"})
        except Refused as refusal:
            self._send(403, {"error": str(refusal)})
        except json.JSONDecodeError:
            self._send(400, {"error": "that was not JSON"})


class Bridge(ThreadingHTTPServer):
    """The server, carrying the few things a request needs."""

    def __init__(
        self,
        address: tuple[str, int],
        gateway_url: str,
        ledger: Ledger | None = None,
        chosen_file: pathlib.Path | None = None,
    ) -> None:
        """Listen on `address`, talking to the gateway at `gateway_url`."""
        super().__init__(address, _Handler)
        self.gateway_url = gateway_url
        self.ledger = ledger or Ledger()
        self.capabilities = Capabilities()
        self.watching: list[dict[str, Any]] = []
        self.watching_lock = threading.Lock()
        # The transcript belongs here rather than in the page. The delegation
        # guide asks the application to keep it, and a page keeps it only until
        # it is reloaded.
        self.spoken: list[tuple[float, str, str]] = []
        #: The run whose permission question is open, if one is.
        self.awaiting: str | None = None
        #: The run the last request left unfinished, if it left one.
        self.following: str | None = None
        #: A phrase the last answer insisted on hearing back word for word.
        self.demanded: str | None = None
        #: Where the person is, if the browser was allowed to say. Held here and
        #: nowhere else: never written to disk, never sent to an agent.
        self.placed: str | None = None
        #: claude-voice, when there is a token to reach it with. ADR-VI-024.
        self.sessions: sessions.Client | None = None
        #: Requests Claude Code sessions are waiting on, by number, with what was said.
        self.asked: dict[str, str] = {}
        self.told = 0
        #: Who a turn goes to, kept where a restart finds it. ADR-VI-026.
        self.chosen_file = chosen_file
        self.chosen = target.load(chosen_file)
        #: The gateway's runs that have not finished, so "avbryt" can stop them.
        self.open_runs: set[str] = set()
        #: Sessions whose owed answer was cancelled, and should not be read out.
        self.dropped: set[str] = set()
        #: The busy sessions whose answer the bridge is waiting for, by name.
        self.answers_awaited: dict[str, threading.Thread] = {}
        #: Whether the last answer is for the voice to know rather than to say.
        self.quiet = False
        # Set by a spoken "legg på": the page puts the microphone down after saying so.
        self.hanging_up = False
        #: Who speaks for each kind of target. ADR-VI-027.
        self.voices = target.load_voices(target.voices_file(chosen_file))
        #: What was worth saying, and how far it was heard, kept where a
        #: restart finds it. ADR-VI-029.
        self.news_file = chosen_file.with_name("news.json") if chosen_file else None
        self.cursor: str | None = None
        self.heard = 0
        self.kept: list[dict[str, Any]] = []
        self._recall()
        #: When each run was last asked after, so an answer nobody waits for
        #: can be told as news instead of going nowhere.
        self.polled: dict[str, float] = {}
        #: Every turn measured, kept for weeks. ADR-VI-031.
        self.store = metrics.Store(chosen_file.with_name("metrics.sqlite") if chosen_file else None)
        #: The session tree as last fetched, until `tree_changed` says otherwise.
        self.shape: list[dict[str, Any]] | None = None

    def remember(self, who: str, text: str) -> None:
        """Keep a turn, for whoever needs to know what was already said."""
        if not text.strip():
            return
        self.spoken.append((time.time(), "user" if who == "You" else "assistant", text.strip()))
        del self.spoken[: -live.TURNS_REMEMBERED * 2]

    def _worth_keeping(self) -> list[tuple[str, str]]:
        """The turns worth passing on: recent enough, few enough, short enough."""
        oldest = time.time() - REMEMBER_FOR_SECONDS
        fresh = [(role, text) for when, role, text in self.spoken if when >= oldest]
        kept: list[tuple[str, str]] = []
        room = HISTORY_CHARACTERS
        for role, text in reversed(fresh[-live.TURNS_REMEMBERED :]):
            if len(text) > room:
                break
            room -= len(text)
            kept.insert(0, (role, text))
        return kept

    def recent(self) -> list[dict[str, Any]]:
        """The turns a new voice session is given, in the shape it takes."""
        # A user message carries `input_text` and an assistant one
        # `output_text`; a plain string is refused outright, which is how this
        # was found. The list takes 128 messages and 8,192 tokens together.
        return [
            {
                "type": "message",
                "role": role,
                # RULE: a remembered turn is a message item, not a bare string
                "content": [{"type": "input_text" if role == "user" else "output_text", "text": text}],
            }
            for role, text in self._worth_keeping()
        ]

    def context_turns(self) -> list[tuple[str, str]]:
        """The turns worth passing on, as (role, text)."""
        return self._worth_keeping()

    def context(self) -> list[dict[str, str]]:
        """The same turns, in the shape the gateway takes them.

        The gateway plans against what was said, and most of what was said it
        never hears: the voice answers small talk itself. Without this, "run the
        tests there" arrives with no idea what "there" is.
        """
        return [{"role": role, "content": text} for role, text in self._worth_keeping()]

    def follow(self, run_id: str, asked: str) -> None:
        """Relay a run's events to whoever is watching, on its own thread."""
        # The turn that started it is waiting for it now.
        self.polled[run_id] = time.monotonic()
        self.open_runs.add(run_id)
        notice(self, {"event": "run.asked", "run_id": run_id, "asked": asked})

        def read() -> None:
            try:
                for event in gateway.events(run_id, self.gateway_url):
                    notice(self, event)
                    if event.get("event") in ("run.completed", "run.failed"):
                        self.open_runs.discard(run_id)
                    if event.get("event") == "run.completed":
                        self.run_finished(run_id, str(event.get("output") or ""))
            except (OSError, Refused) as failure:
                notice(self, {"event": "watch.lost", "run_id": run_id, "why": str(failure)})

        threading.Thread(target=read, daemon=True).start()

    def choose(self, chosen: target.Target) -> None:
        """Send turns somewhere else from now on."""
        self.chosen = chosen
        known = {s.get("name"): s.get("claude_session_id") for s in self.running()} if chosen.name else {}
        # RULE: the choice survives a restart
        target.save(self.chosen_file, chosen, str(known.get(chosen.name) or ""))

    def voice_now(self) -> str:
        """The voice the chosen target speaks with."""
        return self.voices.get(self.chosen.kind, target.VOICE_DEFAULTS["voice"])

    def revoice(self, kind: str, voice: str) -> bool:
        """Give one kind of target another voice, if the service offers it."""
        # RULE: a voice the service does not offer is never sent
        if voice not in live.VOICES or kind not in target.VOICE_DEFAULTS:
            return False
        self.voices[kind] = voice
        target.save_voices(target.voices_file(self.chosen_file), self.voices)
        return True

    def running(self) -> list[dict[str, Any]]:
        """The Claude Code sessions running now, or none when claude-voice cannot be asked."""
        if self.sessions is None:
            return []
        try:
            found = self.sessions.call("list_active_sessions", {}).get("sessions") or []
        except (OSError, Refused):
            return []
        # A session claude-voice runs itself is reached with a task, not a
        # message, so it cannot be talked to this way yet.
        return [s for s in found if isinstance(s, dict) and s.get("name") and not s.get("managed_by_bridge")]

    def _settle(self, item: dict[str, Any]) -> dict[str, Any]:
        """Act on one piece of news, and return it as it should be told."""
        if item.get("kind") == "needs_approval" and item.get("approval_id") is not None:
            self.asked[str(item["approval_id"])] = str(item.get("text", ""))
        elif item.get("kind") == "tree_changed":
            self.shape = None
        elif item.get("kind") == "approval_expired":
            # Refused for nobody answering, so a yes can no longer reach it.
            self.asked.pop(str(item.get("approval_id")), None)
        elif item.get("kind") == "ended" and self.chosen.name == str(item.get("session")):
            # Otherwise the person keeps talking into a session that is gone.
            self.choose(target.Target("voice"))
            told = f"{item.get('session')} has ended, so you are talking to the voice again."
            return {**item, "kind": "error", "text": told}
        return item

    def _recall(self) -> None:
        """Pick up the news where the last run of the bridge left it."""
        if self.news_file is None:
            return
        try:
            kept = json.loads(self.news_file.read_text())
        except (OSError, ValueError):
            return
        self.cursor = kept.get("cursor") or None
        self.told = int(kept.get("told", 0))
        self.heard = int(kept.get("heard", 0))
        self.kept = [k for k in kept.get("kept", []) if isinstance(k, dict)]

    def _keep(self) -> None:
        if self.news_file is None:
            return
        self.news_file.parent.mkdir(parents=True, exist_ok=True)
        self.news_file.write_text(
            json.dumps({"cursor": self.cursor, "told": self.told, "heard": self.heard, "kept": self.kept})
        )

    def placed_in_news(self, cursor: str) -> None:
        """Remember how far claude-voice's news has been read."""
        if cursor == self.cursor:
            return
        self.cursor = cursor
        # RULE: the place in the news survives a restart
        self._keep()

    def heard_up_to(self, seq: int) -> None:
        """The page said everything up to here aloud."""
        if seq > self.heard:
            self.heard = seq
            self._keep()

    def missed(self) -> str:
        """What was worth saying and was not heard, to say first next time."""
        unheard = [k for k in self.kept if int(k.get("seq", 0)) > self.heard]
        # The same sentence six times over is one piece of news, said once.
        latest_of = {str(k.get("said")): k for k in unheard}
        unheard = sorted(latest_of.values(), key=lambda k: int(k.get("seq", 0)))
        if not unheard:
            return ""
        latest = unheard[-MISSED_SPOKEN:]
        said = " ".join(str(k.get("said", "")) for k in latest)
        more = len(unheard) - len(latest)
        tail = f" And {more} more, on the screen." if more else ""
        self.heard_up_to(int(unheard[-1].get("seq", 0)))
        return f"While you were away: {said}{tail}"

    def run_finished(self, run_id: str, output: str) -> None:
        """An answer from the gateway; told as news if nobody is waiting for it."""
        # RULE: an answer nobody waited for becomes news
        if time.monotonic() - self.polled.get(run_id, 0.0) < UNWATCHED_SECONDS:
            return
        self.hear([{"session": "Hermes", "kind": "finished", "text": f"Hermes answered: {output[:300]}"}])

    def fleet(self) -> list[dict[str, Any]]:
        """What every session is doing, one line each, in one call to claude-voice."""
        if self.sessions is None:
            return []
        try:
            found = self.sessions.call("fleet_recap", {}).get("sessions") or []
        except (OSError, Refused):
            return []
        return [s for s in found if isinstance(s, dict) and s.get("name")]

    def fleet_said(self) -> str:
        """The fleet, in a few sentences: what waits on the person first, then what is busy."""
        order = {"waiting": 0, "busy": 1, "shell": 1}
        doing = sorted(
            (s for s in self.fleet() if s.get("doing")), key=lambda s: order.get(str(s.get("status")), 2)
        )
        if not doing:
            return "Ingen av øktene har noe å melde akkurat nå."
        said = [f"{s['name']}: {_ended(str(s['doing']))}" for s in doing[:FLEET_SPOKEN]]
        more = len(doing) - len(said)
        return " ".join(said) + (f" Og {more} til, på skjermen." if more else "")

    def digest_said(self, asked: str) -> str:
        """One session's long conversation, summed up by claude-voice in the voice's language."""
        found = target.matching(asked, self.running())
        if len(found) != 1:
            return (
                f"No running session is called {asked}."
                if not found
                else f"{asked} could be {', '.join(found)}. Which one?"
            )
        if self.sessions is None:
            return "I cannot reach the coding sessions."
        language = live.LANGUAGE_NAMES.get(live.LANGUAGE, live.LANGUAGE)
        try:
            # A model writes it on claude-voice's side: seconds, not milliseconds.
            got = self.sessions.call(
                "digest_session", {"session": found[0], "language": language}, waits=DIGEST_SECONDS
            )
        except (OSError, Refused) as failure:
            return f"I could not sum up {found[0]}: {str(failure)[:120]}"
        # Fit to be heard, like any other answer: whole sentences, never a trailing "…".
        return (
            answer_in({"reply": str(got.get("digest") or "")})
            or f"There was nothing to sum up in {found[0]}."
        )

    def usage(self) -> dict[str, Any]:
        """Minutes of voice and what they cost: day by day this month, and month by month."""
        per_minute = budget.USD_PER_MINUTE
        days = [
            {**day, "usd": round(day["minutes"] * per_minute, 2)} for day in metrics.voice_by_day(self.store)
        ]
        months = [
            {"month": month, "minutes": round(seconds / 60, 1), "usd": round(seconds / 60 * per_minute, 2)}
            for month, seconds in self.ledger.by_month().items()
        ]
        return {"days": days, "months": months, "ceiling_minutes": int(budget.ceiling_usd() / per_minute)}

    def health(self) -> dict[str, Any]:
        """How the bridge and claude-voice are doing, in one read: now, lately, and against last week."""
        mine = metrics.summary(self.store)
        mine["now"]["memory"] = metrics.memory()
        theirs: dict[str, Any]
        if self.sessions is None:
            theirs = {"unreachable": "claude-voice is not configured"}
        else:
            try:
                theirs = self.sessions.call("health", {})
            except (OSError, Refused) as failure:
                theirs = {"unreachable": str(failure)[:200]}
        return {"bridge": mine, "claude_voice": theirs}

    def tree(self) -> list[dict[str, Any]]:
        """Every session claude-voice knows of, with who started and who messaged whom.

        Kept until claude-voice says it changed. A page open on two devices
        would otherwise rebuild it every few seconds for nothing.
        """
        if self.sessions is None:
            return []
        if self.shape is None:
            try:
                nodes = self.sessions.call("session_tree", {}).get("nodes") or []
            except (OSError, Refused):
                return []
            self.shape = [n for n in nodes if isinstance(n, dict) and n.get("id")]
        return self.shape

    def await_answer(self, name: str, after: int, said: str = "") -> str:
        """Wait in the background for a busy session's answer, and tell it as news when it comes."""
        if name in self.answers_awaited and self.answers_awaited[name].is_alive():
            # Already waiting: this one is passed on too, without another "busy".
            self.quiet = True
            return f"Also passed on to {name}. Its answer comes when it is free."

        def wait() -> None:
            answer, done = follow_chosen(self, f"claude:{after}:{name}", ANSWER_PATIENCE_SECONDS, said=said)
            if done and answer:
                self.hear([{"session": name, "kind": "answer", "text": answer}])

        waiting = threading.Thread(target=wait, daemon=True)
        self.answers_awaited[name] = waiting
        waiting.start()
        return f"{name} is busy with something else. I will say its answer when it comes."

    def _spoken_to(self, item: dict[str, Any]) -> bool:
        """News about the session somebody is talking to, which they hear anyway."""
        # Every turn of a chosen session ends in "has finished and is waiting";
        # its answer is the news, and that comes as the answer. A permission
        # question from it is still news.
        return (
            self.chosen.kind == "session"
            and str(item.get("session")) == self.chosen.name
            and item.get("kind") in ("finished", "needs_input")
        )

    def hear(self, news: list[dict[str, Any]]) -> None:
        """Put news from the coding sessions where the page will find it."""
        for heard in news:
            item = self._settle(heard)
            self.told += 1
            # A session's answer, arriving after the turn that asked for it, is
            # said like any other news.
            aloud = item.get("kind") in (*sessions.SPOKEN, "answer") and not self._spoken_to(item)
            if item.get("kind") == "answer" and str(item.get("session")) in self.dropped:
                # Cancelled while it was still owed: shown, never said.
                self.dropped.discard(str(item.get("session")))
                aloud = False
            notice(
                self,
                {
                    "event": "claude.news",
                    "seq": self.told,
                    "session": str(item.get("session", "")),
                    "kind": str(item.get("kind", "")),
                    "said": str(item.get("text", "")),
                    "aloud": aloud,
                    "approval_id": item.get("approval_id"),
                },
            )
            if aloud:
                said = sessions.spoken(str(item.get("text", "")))
                self.kept = [*self.kept, {"seq": self.told, "said": said}][-KEPT_NEWS:]
        self._keep()

    def listen(self, client: sessions.Client, every: float = sessions.POLL_SECONDS) -> None:
        """Ask claude-voice what is new, on its own thread, for as long as this runs."""
        self.sessions = client
        client.store = client.store or self.store
        if self.chosen.kind == "session":
            # Kept by name across a restart; its id may have changed meanwhile,
            # and the chosen session's own hooks know it only by that.
            self.choose(self.chosen)

        def poll() -> None:
            lost = False
            while True:
                try:
                    cursor, news = sessions.news(client, self.cursor)
                    lost = False
                    self.hear(news)
                    self.placed_in_news(cursor)
                except (OSError, Refused, ValueError) as failure:
                    if not lost:
                        notice(self, {"event": "claude.lost", "why": str(failure)})
                    lost = True
                time.sleep(every)

        threading.Thread(target=poll, daemon=True).start()
