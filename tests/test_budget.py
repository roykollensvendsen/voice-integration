"""What the month's ceiling allows, and what it refuses.

Voice is the only part of this system billed by the second, and it bills while
nobody is speaking. The ceiling is the one mechanism between an open microphone
and a surprise.
"""

import pytest

from voice_bridge import budget
from voice_bridge.policy import Refused


def test_the_ceiling_is_twenty_dollars_a_month():
    assert budget.DEFAULT_CEILING_USD == 20.00
    assert budget.USD_PER_MINUTE == 0.05


def test_a_fresh_month_allows_the_whole_ceiling(tmp_path):
    ledger = budget.Ledger(tmp_path / "spend.json")
    assert ledger.remaining_usd() == 20.00
    assert ledger.remaining_minutes() == 400


def test_seconds_spent_come_off_the_ceiling(tmp_path):
    ledger = budget.Ledger(tmp_path / "spend.json")
    ledger.record(600)
    assert ledger.remaining_usd() == pytest.approx(19.50)
    assert ledger.remaining_minutes() == 390


def test_what_was_spent_survives_the_process(tmp_path):
    budget.Ledger(tmp_path / "spend.json").record(120)
    assert budget.Ledger(tmp_path / "spend.json").remaining_usd() == pytest.approx(19.90)


def test_a_session_is_refused_once_the_monthly_ceiling_is_spent(tmp_path):
    ledger = budget.Ledger(tmp_path / "spend.json")
    ledger.authorise()
    ledger.record(400 * 60)
    with pytest.raises(Refused, match="ceiling"):
        ledger.authorise()


def test_a_new_month_starts_again(tmp_path):
    ledger = budget.Ledger(tmp_path / "spend.json", month="2026-08")
    ledger.record(400 * 60)
    assert budget.Ledger(tmp_path / "spend.json", month="2026-09").remaining_usd() == 20.00
