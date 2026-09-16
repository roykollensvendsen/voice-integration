"""The thinnest whole path: a voice tool call in, a sentence to speak out.

Everything between is the real thing — the permission layer, the request
planner, an HTTP socket, a server answering the contract, and the renderer that
decides what a person hears. Only the microphone and the model are missing, and
they are the two parts that cannot run in continuous integration.
"""

import pytest

from voice_bridge import gateway
from voice_bridge.policy import Capabilities, Refused


def test_a_spoken_task_starts_a_run_and_answers_with_its_identifier(url, hermes, run_id):
    spoken = gateway.call(
        "agent_task",
        {"agent": "claude-code", "instruction": "run the tests", "room": "evening"},
        url,
        key="secret",
    )
    assert spoken == f"Started. The run is {run_id}."
    path, body, authorization = hermes.seen[0]
    assert path == "/v1/runs"
    assert body == {"input": "run the tests", "model": "claude-code", "session_id": "evening"}
    assert authorization == "Bearer secret"


def test_the_person_can_ask_what_a_run_is_doing(url, run_id):
    assert gateway.call("run_status", {"run_id": run_id}, url) == (
        "That run is running, last event tool.started."
    )


def test_the_person_can_answer_an_approval_by_voice(url, hermes, run_id):
    spoken = gateway.call("approval_resolve", {"run_id": run_id, "choice": "deny"}, url)
    assert spoken == "Answered deny, for this one call."
    assert hermes.seen[0][1] == {"choice": "deny"}


def test_the_person_can_steer_and_stop(url, run_id):
    assert gateway.call("run_steer", {"run_id": run_id, "guidance": "leave git alone"}, url) == (
        "Passed it on."
    )
    assert gateway.call("run_stop", {"run_id": run_id}, url) == "Stopping. The run is stopping."


def test_the_person_can_pick_a_room_back_up(url):
    assert gateway.call("session_recall", {}, url) == "2 open: evening, morning."


def test_a_capability_the_session_lacks_never_reaches_the_gateway(url, hermes, run_id):
    only_reading = Capabilities(frozenset({"run_status"}))
    with pytest.raises(Refused):
        gateway.call("run_stop", {"run_id": run_id}, url, only_reading)
    assert hermes.seen == []
