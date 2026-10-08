"""What a newcomer is told is still missing, and that it never shows a secret."""

import json

from voice_bridge import budget, ready
from voice_bridge.cli import main


def checked(environ, tmp_path, *, offline=True, answers=None):
    """The checks for `environ`, with every address answering as `answers` says."""
    answers = answers or {}

    def status(url, _headers):
        return next((code for part, code in answers.items() if part in url), 0)

    return {
        c.name: c
        for c in ready.checks(
            environ,
            offline=offline,
            ledger=budget.Ledger(tmp_path / "spent.json"),
            gateway="http://127.0.0.1:8642",
            claude_voice_file=tmp_path / "claude-voice-env",
            status=status,
        )
    }


def test_a_missing_key_is_named_with_the_one_thing_to_do(tmp_path):
    found = checked({"OPENAI_API_KEY": ""}, tmp_path)
    assert not found["openai_key"].ok
    assert "~/.config/voice-bridge/env" in found["openai_key"].fix
    assert not ready.summary(list(found.values()))["ready"]


def test_the_voice_alone_is_ready_with_a_key_and_a_budget(tmp_path):
    found = checked({"OPENAI_API_KEY": "sk-test"}, tmp_path)
    assert found["openai_key"].ok
    assert found["budget"].ok
    assert not found["hermes"].required
    assert not found["claude_voice"].required
    assert ready.summary(list(found.values()))["ready"]


def test_a_key_openai_refuses_is_not_ready(tmp_path):
    found = checked({"OPENAI_API_KEY": "sk-test"}, tmp_path, offline=False, answers={"openai.com": 401})
    assert not found["openai_key"].ok
    assert "refused" in found["openai_key"].detail


def test_the_planner_and_the_sessions_pass_when_they_answer(tmp_path):
    (tmp_path / "claude-voice-env").write_text("CLAUDE_VOICE_TOKEN=abc\n")
    answers = {"openai.com": 200, "8642": 200, "8811": 200}
    found = checked(
        {"OPENAI_API_KEY": "sk-test", "HERMES_API_KEY": "h"}, tmp_path, offline=False, answers=answers
    )
    assert all(c.ok for c in found.values()), [c for c in found.values() if not c.ok]


def test_claude_voice_without_its_token_is_not_counted_as_there(tmp_path):
    found = checked(
        {"OPENAI_API_KEY": "sk-test"}, tmp_path, offline=False, answers={"8811": 200, "openai.com": 200}
    )
    assert not found["claude_voice"].ok
    assert "CLAUDE_VOICE_TOKEN" in found["claude_voice"].fix


def test_the_settings_file_fills_in_only_what_the_environment_lacks(tmp_path):
    file = tmp_path / "env"
    file.write_text('OPENAI_API_KEY="from-file"\nNTFY_TOPIC=t\n# a comment\n')
    environ = {"NTFY_TOPIC": ""}
    ready.apply_settings(environ, file)
    assert environ == {"OPENAI_API_KEY": "from-file", "NTFY_TOPIC": ""}


def test_no_check_ever_prints_a_secret(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-very-secret-value")
    monkeypatch.setenv("HERMES_API_KEY", "hermes-very-secret")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    main(["ready", "--offline"])
    main(["ready", "--offline", "--json"])
    out = capsys.readouterr().out
    assert "very-secret" not in out
    assert json.loads(out[out.index("{") :])["ready"] is True
