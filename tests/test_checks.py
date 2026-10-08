import pandas as pd

from pharma.quality import checks


def daily(dates, quantities=None, atc="R06"):
    dates = pd.to_datetime(dates)
    return pd.DataFrame({
        "date": dates, "hour": pd.array([pd.NA] * len(dates), dtype="Int8"), "atc": atc,
        "quantity": quantities if quantities is not None else [1.0] * len(dates),
        "source": "daily", "granularity": "daily",
    })


def test_real_data_has_no_anomaly(real_long):
    assert checks.missing_days(real_long).empty
    assert checks.duplicates(real_long).empty
    assert checks.negatives(real_long).empty


def test_missing_day_detected():
    df = daily(["2019-01-01", "2019-01-02", "2019-01-04"])
    assert checks.missing_days(df)["date"].tolist() == [pd.Timestamp("2019-01-03")]


def test_missing_hour_detected(real_long):
    hourly = real_long[real_long["source"] == "hourly"]
    hole = (hourly["date"] == "2016-05-04") & (hourly["hour"] == 14)
    missing = checks.missing_days(hourly[~hole])
    assert missing[["date", "hour"]].values.tolist() == [[pd.Timestamp("2016-05-04"), 14]]


def test_duplicates_negatives_non_integers():
    df = daily(["2019-01-01", "2019-01-01", "2019-01-02", "2019-01-03"], [1.0, 1.0, -2.0, 99.75000000000003])
    assert len(checks.duplicates(df)) == 2
    assert checks.negatives(df)["quantity"].tolist() == [-2.0]
    assert checks.non_integers(df)["quantity"].round(2).tolist() == [99.75]


def test_float_noise_is_not_non_integer():
    assert checks.non_integers(daily(["2019-01-01"], [3.0000000000004])).empty


def test_month_coverage_handles_leap_years():
    df = daily(pd.date_range("2016-02-01", "2016-02-29"))
    cov = checks.month_coverage(df).iloc[0]
    assert (cov["days_present"], cov["days_in_month"], cov["ratio"]) == (29, 29, 1.0)


def test_last_complete_month_is_computed(real_long, real_settings):
    last = checks.last_complete_month(real_long, real_settings.quality["incomplete_month_ratio"])
    assert last == pd.Period("2019-09", "M")
