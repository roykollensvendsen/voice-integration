"""One test per rule, named so that a mutation run says which rule went unguarded.

`python scripts/mutate.py` switches each rule off in turn and expects a named
test here to go red. Read a kill as carefully as a survival: the test that goes
red has to be the one this file names for that rule, or the rule is guarded by
an accident.
"""

import pytest

from voice_bridge import speech
from voice_bridge.policy import Capabilities, Refused


def test_a_voice_session_may_only_call_a_tool_it_was_given():
    only_reading = Capabilities(frozenset({"run_status"}))
    only_reading.permit("run_status", {"run_id": "run_ab12"})
    with pytest.raises(Refused, match="not in this voice session's capabilities"):
        only_reading.permit("run_stop", {"run_id": "run_ab12"})


@pytest.mark.parametrize("choice", ["session", "always"])
def test_an_approval_answered_by_voice_binds_one_call_only(choice):
    with pytest.raises(Refused, match="would outlive this call"):
        Capabilities().permit("approval_resolve", {"run_id": "run_ab12", "choice": choice})


@pytest.mark.parametrize("choice", ["once", "deny"])
def test_the_per_call_answers_are_still_allowed(choice):
    Capabilities().permit("approval_resolve", {"run_id": "run_ab12", "choice": choice})


def test_a_spoken_reply_is_capped_so_audio_never_carries_a_transcript():
    transcript = "The agent reported a failure in the parser. " * 40
    spoken = speech.shorten(transcript)
    assert len(spoken) <= speech.SPOKEN_REPLY_MAX_CHARS
    assert spoken.endswith("…")


def test_a_short_reply_is_left_alone():
    assert speech.shorten("  That run is  running. ") == "That run is running."
