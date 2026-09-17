"""The contract itself: the surface, the schemas, and the requests they become."""

import json
import pathlib

from voice_bridge import check as drift
from voice_bridge import gateway
from voice_bridge.contract import BY_NAME, VOICE_TOOLS

ROOT = pathlib.Path(__file__).parent.parent


def test_the_documents_and_the_code_still_agree():
    assert drift.report(ROOT) == [
        "voice tools: 6 in docs/voice-contract.md, 6 in the code, agreed",
        "gateway paths: 7 in docs/hermes-contract.md, 7 in the code, agreed",
        "rules: 24 in the source, 24 in scripts/mutations.toml, agreed",
        "rule tests: 24 rules, each with a test named after it",
    ]


def test_every_rule_marked_in_the_source_has_a_mutation_row():
    """Without this the evidence table quietly becomes a historical document."""
    assert drift.marked_rules(ROOT) == drift.rowed_rules(ROOT)


def test_every_rule_has_a_test_named_after_it():
    """A kill is only readable when the test that went red names the rule."""
    named = drift.test_names(ROOT)
    assert [r for r in sorted(drift.marked_rules(ROOT)) if drift.test_name_for(r) not in named] == []


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


def test_an_optional_argument_left_out_is_left_out_of_the_body():
    planned = gateway.plan("agent_task", {"agent": "opencode", "instruction": "look"})
    assert planned.body == {"input": "look", "model": "opencode"}
