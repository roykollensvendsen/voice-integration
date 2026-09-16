"""The contract itself: the surface, the schemas, and the requests they become."""

import json
import pathlib

import pytest

from voice_bridge import check as drift
from voice_bridge import gateway
from voice_bridge.contract import BY_NAME, VOICE_TOOLS
from voice_bridge.policy import Refused

ROOT = pathlib.Path(__file__).parent.parent


def test_the_documents_and_the_code_still_agree():
    assert drift.report(ROOT) == [
        "voice tools: 6 in docs/voice-contract.md, 6 in the code, agreed",
        "gateway paths: 6 in docs/hermes-contract.md, 6 in the code, agreed",
        "rules: 3 in the source, 3 in scripts/mutations.toml, agreed",
    ]


def test_every_rule_marked_in_the_source_has_a_mutation_row():
    """Without this the evidence table quietly becomes a historical document."""
    assert drift.marked_rules(ROOT) == drift.rowed_rules(ROOT)


def test_the_surface_is_six_tools_and_stays_six_by_decision():
    assert len(VOICE_TOOLS) == 6
    assert len(BY_NAME) == len(VOICE_TOOLS)


def test_every_schema_is_the_shape_a_realtime_session_takes():
    for schema in gateway.tool_schemas():
        assert schema["type"] == "function"
        parameters = schema["parameters"]
        assert parameters["additionalProperties"] is False
        assert set(parameters["required"]) <= set(parameters["properties"])
        json.dumps(schema)


def test_a_path_argument_is_substituted_rather_than_sent_as_a_field():
    planned = gateway.plan("run_steer", {"run_id": "run_ab12", "guidance": "stop that"})
    assert planned.url.endswith("/v1/runs/run_ab12/steer")
    assert planned.body == {"input": "stop that"}


def test_an_optional_argument_left_out_is_left_out_of_the_body():
    planned = gateway.plan("agent_task", {"agent": "opencode", "instruction": "look"})
    assert planned.body == {"input": "look", "model": "opencode"}


def test_a_missing_required_argument_is_refused_before_anything_is_sent():
    with pytest.raises(Refused, match="needs instruction"):
        gateway.plan("agent_task", {"agent": "opencode"})


def test_a_gateway_url_that_is_not_http_is_refused():
    with pytest.raises(Refused, match="not HTTP"):
        gateway.send(gateway.Request("GET", "file:///etc/passwd", None))
