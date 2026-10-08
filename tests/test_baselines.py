import pandas as pd
import pytest

from pharma.forecast.baselines import Naive, SeasonalNaive, future_index


def monthly(values, start="2017-10"):
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"), dtype="float64")


def test_naive_repeats_last_value_on_following_months():
    pred = Naive().fit(monthly([1, 2, 3], start="2019-01")).predict(2)
    assert pred.tolist() == [3.0, 3.0]
    assert pred.index.tolist() == [pd.Period("2019-04", "M"), pd.Period("2019-05", "M")]


def test_seasonal_naive_uses_same_month_last_year():
    y = monthly(range(24))  # 2017-10 → 2019-09, valeur = rang du mois
    pred = SeasonalNaive(period=12).fit(y).predict(14)
    assert pred.index[0] == pd.Period("2019-10", "M")
    assert pred[pd.Period("2019-10", "M")] == y[pd.Period("2018-10", "M")] == 12
    assert pred[pd.Period("2020-09", "M")] == y[pd.Period("2019-09", "M")] == 23
    assert pred[pd.Period("2020-10", "M")] == 12  # au-delà d'un an, le dernier cycle se répète
    assert pred[pd.Period("2020-11", "M")] == 13


def test_seasonal_naive_needs_a_full_cycle():
    with pytest.raises(ValueError, match="au moins 12"):
        SeasonalNaive(period=12).fit(monthly(range(11)))


def test_future_index_requires_period_index():
    with pytest.raises(TypeError):
        future_index(pd.date_range("2019-01-31", periods=3, freq="ME"), 1)
