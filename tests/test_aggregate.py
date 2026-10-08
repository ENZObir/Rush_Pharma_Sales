import pytest

from pharma.features.aggregate import aggregate


def test_weekly_label_is_sunday_and_matches_export(real_long):
    weekly = aggregate(real_long[real_long["source"] == "daily"], "W")
    first = weekly[weekly["atc"] == "N02BE"].iloc[0]
    assert first["date"].day_name() == "Sunday"
    assert first["quantity"] == pytest.approx(185.95)
    assert (weekly["granularity"] == "weekly").all()


def test_monthly_label_is_month_end(real_long):
    monthly = aggregate(real_long[real_long["source"] == "daily"], "M")
    assert monthly["date"].dt.is_month_end.all()


def test_sources_never_summed_together(real_long):
    out = aggregate(real_long, "M")
    assert out.groupby(["source", "atc", "date"], observed=True).size().max() == 1
    assert set(out["source"]) == set(real_long["source"])


def test_hourly_to_daily_matches_daily_export(real_long):
    recomputed = aggregate(real_long[real_long["source"] == "hourly"], "D").set_index(["date", "atc"])["quantity"]
    daily = real_long[real_long["source"] == "daily"].set_index(["date", "atc"])["quantity"]
    assert (recomputed - daily).abs().max() < 1e-6


def test_unknown_granularity_rejected(real_long):
    with pytest.raises(ValueError):
        aggregate(real_long, "Y")
