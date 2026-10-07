import pytest


@pytest.mark.skip(reason="à écrire avec quality/reconciliation.py")
def test_hourly_sums_to_daily():
    """La réagrégation horaire → journalière doit matcher Daily.csv à la tolérance près."""
