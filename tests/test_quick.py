"""What the bridge answers itself, and everything it refuses to.

Every request used to reach the gateway, which carries thirty-three thousand
tokens of preamble before reading the question. Twelve seconds to be told the
time. These are the few where the bridge is the authority, and the list is
short on purpose.
"""

import re

from voice_bridge import budget, quick, server


def bridge(tmp_path, following=None):
    made = server.Bridge(("127.0.0.1", 0), "http://127.0.0.1:1", budget.Ledger(tmp_path / "s.json"))
    made.following = following
    return made


def test_a_question_the_bridge_can_answer_never_travels_further(tmp_path):
    made = bridge(tmp_path)
    try:
        assert re.match(r"Klokka er \d\d:\d\d\.", quick.answer(made, "Hva er klokka?") or "")
        assert "dollar igjen" in (quick.answer(made, "Hvor mye er igjen?") or "")
        assert quick.answer(made, "Hva kjører nå?") is not None
    finally:
        made.server_close()


def test_what_is_running_reads_the_run_the_bridge_is_following(tmp_path):
    idle, busy = bridge(tmp_path), bridge(tmp_path, following="run_ab12")
    try:
        assert quick.answer(idle, "Hva kjører nå?") == "Ingenting kjører akkurat nå."
        assert quick.answer(busy, "Hva kjører nå?") == "Noe kjører fortsatt."
    finally:
        idle.server_close()
        busy.server_close()


def test_only_a_short_question_is_ever_answered_without_the_gateway(tmp_path):
    """Asking when a failed run started is the gateway's question, not this one."""
    made = bridge(tmp_path)
    try:
        long_one = "Hva er klokka nå, og hvilken kjøring var det som feilet i testene tidligere i dag?"
        assert quick.answer(made, long_one) is None
    finally:
        made.server_close()


def test_real_work_is_never_answered_here(tmp_path):
    made = bridge(tmp_path)
    try:
        for asked in ("Kjør testene", "Spør Claude Code hva prosjektet gjør", "Lag en fil"):
            assert quick.answer(made, asked) is None
    finally:
        made.server_close()


def test_a_question_for_the_web_is_asked_of_the_web_not_of_an_agent(tmp_path, monkeypatch):
    """Looking something up does not need an agent, a repository or twelve seconds."""
    asked = {}

    def instead(question, key=None):  # noqa: ARG001 — the signature it replaces
        asked["question"] = question
        return "Antonelli vant."

    monkeypatch.setattr(quick, "on_the_web", instead)
    made = bridge(tmp_path)
    try:
        assert quick.answer(made, "Hvem vant siste Formel 1-løp?") == "Antonelli vant."
        assert asked["question"] == "Hvem vant siste Formel 1-løp?"
        assert quick.answer(made, "Kjør testene") is None
    finally:
        made.server_close()


def test_a_web_answer_loses_its_footnotes_before_it_is_spoken():
    """A spoken URL is noise, and the model writes them inline as links."""
    written = "Antonelli vant. ([formula1.com](https://www.formula1.com/en/latest/x?utm_source=openai))"
    assert quick.CITATION.sub("", written).strip() == "Antonelli vant."


def test_a_place_is_a_name_a_person_can_say(tmp_path):
    made, placed = bridge(tmp_path), bridge(tmp_path)
    placed.placed = "Hillevåg, Stavanger, Norge"
    try:
        assert quick.answer(made, "Hvor er jeg?") == "Jeg vet ikke hvor du er."
        assert quick.answer(placed, "Hvor er jeg?") == "Du er i Hillevåg, Stavanger, Norge."
    finally:
        made.server_close()
        placed.server_close()
