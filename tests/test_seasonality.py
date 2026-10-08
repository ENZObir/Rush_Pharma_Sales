import numpy as np
import pandas as pd
import pytest

from pharma.stats.seasonality import PROFILE_COLUMNS, seasonal_profile


def long_frame(dates, quantity, source, hour=None, atc="R06"):
    return pd.DataFrame({
        "date": pd.DatetimeIndex(dates).normalize(),
        "hour": pd.array(hour if hour is not None else [pd.NA] * len(dates), dtype="Int8"),
        "atc": pd.Categorical([atc] * len(dates)),
        "quantity": np.asarray(quantity, dtype="float64"),
        "source": source,
    })


def test_month_index_neutralises_trend_and_ignores_partial_year():
    dates = pd.date_range("2016-01-31", "2018-03-31", freq="ME")  # 2016, 2017 complètes ; 2018 partielle
    shape = np.where(dates.month == 5, 3.0, 1.0)                  # mai = 3 × les autres mois
    level = np.where(dates.year == 2017, 10.0, 1.0)               # 2017 dix fois plus haute
    quantity = np.where(dates.year == 2018, 1e6, shape * level)   # 2018 aberrante mais incomplète
    out = seasonal_profile(long_frame(dates, quantity, "daily"), "month").set_index("key")["index"]
    assert list(out.index) == [f"{m:02d}" for m in range(1, 13)]
    assert out["05"] == pytest.approx(3 / (14 / 12))
    assert out["01"] == pytest.approx(1 / (14 / 12))
    assert out.mean() == pytest.approx(1.0)


def test_weekday_index_relative_to_overall_daily_mean():
    dates = pd.date_range("2019-01-07", periods=14, freq="D")  # deux semaines, du lundi au dimanche
    quantity = np.where(dates.dayofweek == 0, 8.0, 1.0)         # lundi = 8
    out = seasonal_profile(long_frame(dates, quantity, "daily"), "weekday").set_index("key")["index"]
    assert list(out.index) == [str(d) for d in range(7)]
    assert out["0"] == pytest.approx(8 / (14 / 7))
    assert out["1"] == pytest.approx(1 / 2)


def test_hour_is_a_share_on_complete_days_only():
    full_day = pd.date_range("2019-01-02", periods=24, freq="h")
    partial_day = pd.date_range("2019-01-03 08:00", periods=4, freq="h")
    stamps = full_day.append(partial_day)
    quantity = np.where(stamps.hour == 12, 5.0, 1.0)
    quantity[24:] = 100.0  # journée partielle aberrante, ignorée
    df = long_frame(stamps, quantity, "hourly", hour=stamps.hour)
    out = seasonal_profile(df, "hour").set_index("key")["index"]
    assert list(out.index) == [f"{h:02d}" for h in range(24)]
    assert out.sum() == pytest.approx(1.0)
    assert out["12"] == pytest.approx(5 / 28)


def test_contract_columns_and_guards():
    dates = pd.date_range("2019-01-07", periods=7, freq="D")
    daily = long_frame(dates, np.ones(7), "daily")
    assert list(seasonal_profile(daily, "weekday").columns) == PROFILE_COLUMNS
    with pytest.raises(ValueError, match="une seule source"):
        seasonal_profile(pd.concat([daily, daily.assign(source="hourly")]), "weekday")
    with pytest.raises(ValueError, match="hour"):
        seasonal_profile(daily, "hour")
    with pytest.raises(ValueError, match="dimension"):
        seasonal_profile(daily, "season")
