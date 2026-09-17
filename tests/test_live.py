"""Opening a voice session: what is sent, and what is refused before anything is."""

import pytest

from voice_bridge import budget, live
from voice_bridge.policy import Refused


def test_the_session_is_created_in_client_delegation_mode():
    config = live.session_config()
    assert config["model"] == "gpt-live-1"
    assert config["delegation"] == {"type": "client"}


def test_the_voice_model_is_given_no_tools():
    """ADR-VI-019: in client delegation the Live session runs no tools of ours.

    Which is why the instructions have to say what stands behind it — asked what
    it could do, it answered truthfully that it had nothing.
    """
    assert "tools" not in live.session_config()
    assert "tool_choice" not in live.session_config()


def test_the_instructions_never_carry_a_repository_or_a_catalogue():
    """They name two agents as examples and never a repository or a full list.

    The rule was once "no agent names at all", which was right about the
    preamble not growing with the number of agents and wrong about the cost:
    with nothing named, it told the person it had no tools and no agents, which
    is true of itself and false of the system. Two names in a fixed sentence do
    not grow with anything.
    """
    for written in live.INSTRUCTIONS.values():
        assert "voice-integration" not in written
        assert "/home/" not in written
        assert written.lower().count("code") <= 3
        assert len(written) < 1000


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


def test_the_voice_answers_small_talk_without_asking_the_backend():
    """Ten chatted turns once reached the agents because nothing said not to."""
    assert "småprat" in live.INSTRUCTIONS["nb"]
    assert "small talk" in live.INSTRUCTIONS["en"]
    for written in live.INSTRUCTIONS.values():
        assert len(written) < 1000


def test_the_instructions_do_not_ask_for_an_identifier_to_be_read_out():
    """They once asked for the opposite, written before anything else could show one."""
    for written in live.INSTRUCTIONS.values():
        assert "identifikator" in written or "identifier" in written
        assert "langsomt" not in written
        assert "slowly" not in written


def test_the_voice_never_says_it_has_no_tools():
    """In client delegation it has none, and said so when asked what it could do."""
    for written in live.INSTRUCTIONS.values():
        assert "no tools" in written or "ingen verktøy" in written
        assert "Claude Code" in written
    assert "Si aldri at du ikke har verktøy" in live.INSTRUCTIONS["nb"]
    assert "Never say you have no tools" in live.INSTRUCTIONS["en"]
