import pytest


@pytest.mark.skip(reason="à écrire avec features/calendar.py")
def test_weekday_derived_from_date():
    """1/2/2014 doit donner un jeudi."""
