"""Opening a voice session: what is sent, and what is refused before anything is."""

import pytest

from voice_bridge import budget, live
from voice_bridge.policy import Refused


def test_the_session_is_created_in_client_delegation_mode():
    config = live.session_config()
    assert config["model"] == "gpt-live-1"
    assert config["delegation"] == {"type": "client"}


def test_the_voice_model_is_given_no_tools():
    """ADR-VI-019: in client delegation the Live session runs no tools of ours."""
    assert "tools" not in live.session_config()
    assert "tool_choice" not in live.session_config()


def test_the_instructions_never_carry_a_repository_or_an_agent_name():
    for written in live.INSTRUCTIONS.values():
        assert "hermes" not in written.lower()
        assert "claude" not in written.lower()
        assert len(written) < 400


def test_a_session_is_never_opened_without_a_language_rule_in_its_own_language():
    """An English prompt is why the first real conversation came back in German."""
    assert live.instructions("nb").startswith("Snakk norsk med mindre")
    assert live.instructions("en").startswith("Speak English unless")
    with pytest.raises(Refused, match="must be in the language it speaks"):
        live.instructions("de")


def test_norwegian_is_what_this_installation_speaks():
    assert live.LANGUAGE == "nb"
    assert live.session_config()["instructions"] == live.INSTRUCTIONS["nb"]


def test_the_month_is_checked_before_a_session_is_opened(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "not-used-because-the-month-is-spent")
    ledger = budget.Ledger(tmp_path / "spend.json")
    ledger.record(400 * 60)
    with pytest.raises(Refused, match="ceiling"):
        live.open_session("v=0", ledger)


def test_a_session_without_a_key_is_refused_rather_than_attempted(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(Refused, match="no OPENAI_API_KEY"):
        live.open_session("v=0", budget.Ledger(tmp_path / "spend.json"))
