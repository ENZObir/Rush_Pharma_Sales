import math

import pandas as pd
import pytest

from pharma.forecast.metrics import gain_vs_baseline, mae, mape, mase, mase_scale


def monthly(values, start="2019-01"):
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"), dtype="float64")


Y_TRUE = monthly([10, 20, 0])
Y_PRED = monthly([12, 15, 3])  # erreurs absolues : 2, 5, 3


def test_mae_by_hand():
    assert mae(Y_TRUE, Y_PRED) == pytest.approx(10 / 3)


def test_mae_ignores_months_absent_from_y_true():
    assert mae(Y_TRUE, monthly([12, 15, 3, 999])) == pytest.approx(10 / 3)


def test_mape_excludes_zero_actuals():
    assert mape(Y_TRUE, Y_PRED) == pytest.approx((2 / 10 + 5 / 20) / 2)
    assert math.isnan(mape(monthly([0, 0]), monthly([1, 1])))


def test_mase_scale_is_in_sample_seasonal_naive_mae():
    # écarts à 2 périodes : 4 − 1 = 3 et 8 − 2 = 6
    assert mase_scale(monthly([1, 2, 4, 8]), period=2) == pytest.approx(4.5)
    with pytest.raises(ValueError):
        mase_scale(monthly([1, 2]), period=2)


def test_mase_by_hand():
    assert mase(Y_TRUE, Y_PRED, monthly([1, 2, 4, 8], start="2018-09"), period=2) == pytest.approx((10 / 3) / 4.5)


def test_mase_is_nan_when_history_has_no_seasonal_change():
    assert math.isnan(mase(Y_TRUE, Y_PRED, monthly([5, 5, 5, 5], start="2018-09"), period=2))


def test_gain_vs_baseline():
    assert gain_vs_baseline(8, 10) == pytest.approx(0.2)
    assert gain_vs_baseline(12, 10) == pytest.approx(-0.2)
    assert math.isnan(gain_vs_baseline(1, 0))
