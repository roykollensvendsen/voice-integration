"""One test per rule, named so that a mutation run says which rule went unguarded.

`python scripts/mutate.py` switches each rule off in turn and expects a named
test here to go red. Read a kill as carefully as a survival: the test that goes
red has to be the one this file names for that rule, or the rule is guarded by
an accident.
"""

import pytest

from voice_bridge import gateway, speech
from voice_bridge.cli import main
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


def test_a_path_argument_goes_into_the_url_never_into_the_body():
    planned = gateway.plan("run_steer", {"run_id": "run_ab12", "guidance": "stop that"})
    assert planned.url.endswith("/v1/runs/run_ab12/steer")
    assert planned.body == {"input": "stop that"}


def test_a_required_argument_missing_is_refused_before_a_request_is_planned():
    with pytest.raises(Refused, match="needs instruction"):
        gateway.plan("agent_task", {"agent": "opencode"})


def test_only_an_http_gateway_url_is_ever_opened():
    with pytest.raises(Refused, match="not HTTP"):
        gateway.send(gateway.Request("GET", "file:///etc/passwd", None))


def test_a_gateway_refusal_is_spoken_not_raised(url):
    spoken = gateway.call("run_status", {"run_id": "run_nothing"}, url)
    assert spoken.startswith("The gateway refused that:")


def test_a_refused_call_says_why_and_exits_non_zero(capsys):
    refused = '{"run_id": "run_ab12", "choice": "always"}'
    assert main(["dispatch", "--dry-run", "approval_resolve", refused]) == 2
    assert "refused:" in capsys.readouterr().err


def test_a_run_that_failed_is_not_a_refused_request(url, failed_run_id):
    spoken = gateway.call("run_status", {"run_id": failed_run_id}, url)
    assert not spoken.startswith("The gateway refused")
    assert "failed" in spoken
    assert "Unknown provider" in spoken
