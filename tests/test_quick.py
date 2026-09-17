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
