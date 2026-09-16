"""The command line, exercised through its own entry point rather than a shell.

`tests/test_documented_commands.py` runs these verbs the way a reader meets
them, through a subprocess, and compares what the page says they print. That
covers the happy paths and nothing else: an exit code, a refusal on stderr and a
malformed argument never appear in a document, so they were untested until this
file existed.
"""

import json

import pytest

from voice_bridge.cli import main


def test_the_tool_surface_prints_as_json_a_realtime_session_can_take(capsys):
    assert main(["tools"]) == 0
    schemas = json.loads(capsys.readouterr().out)
    assert [s["name"] for s in schemas] == sorted(s["name"] for s in schemas)
    assert all(s["type"] == "function" for s in schemas)


def test_the_names_alone_are_one_a_line(capsys):
    assert main(["tools", "--names"]) == 0
    assert capsys.readouterr().out.split() == [
        "agent_task",
        "approval_resolve",
        "run_status",
        "run_steer",
        "run_stop",
        "session_recall",
    ]


def test_a_rehearsed_call_prints_the_request_and_sends_nothing(capsys):
    arguments = '{"agent": "claude-code", "instruction": "run the tests"}'
    assert main(["dispatch", "--dry-run", "agent_task", arguments]) == 0
    method, body = capsys.readouterr().out.strip().splitlines()
    assert method == "POST http://localhost:8642/v1/runs"
    assert json.loads(body) == {"input": "run the tests", "model": "claude-code"}


def test_a_call_against_a_running_gateway_prints_one_sentence(capsys, url):
    arguments = json.dumps({"agent": "claude-code", "instruction": "run the tests"})
    assert main(["dispatch", "--gateway", url, "agent_task", arguments]) == 0
    assert capsys.readouterr().out.strip() == "Started. The run is run_ab12."


def test_a_verb_with_no_arguments_needs_none(capsys, url):
    assert main(["dispatch", "--gateway", url, "session_recall"]) == 0
    assert capsys.readouterr().out.strip() == "2 open: evening, morning."


def test_a_tool_that_does_not_exist_is_refused(capsys):
    assert main(["dispatch", "--dry-run", "no_such_tool", "{}"]) == 2
    assert "not in this voice session's capabilities" in capsys.readouterr().err


def test_arguments_that_are_not_json_fail_loudly_rather_than_quietly():
    with pytest.raises(json.JSONDecodeError):
        main(["dispatch", "--dry-run", "run_stop", "not json"])


def test_the_check_reports_every_pair_it_compared(capsys):
    assert main(["check", "."]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == 4


def test_the_check_fails_on_a_tree_that_has_no_documents(capsys, tmp_path):
    assert main(["check", str(tmp_path)]) == 1
    assert "is gone" in capsys.readouterr().err


def test_a_verb_is_required():
    with pytest.raises(SystemExit):
        main([])
