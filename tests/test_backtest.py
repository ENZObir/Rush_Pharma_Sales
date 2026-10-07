import pytest


@pytest.mark.skip(reason="à écrire avec forecast/backtest.py")
def test_no_leakage():
    """Pour chaque origine : max(train.date) < date prévue."""
