import numpy as np
import pandas as pd
import pytest

from pharma.forecast.exogenous import EFFECT_COLUMNS, external_effect, lagged_exog


def external_frame(months, values, variable="syndromes_grippaux"):
    return pd.DataFrame({"month": months, "variable": variable, "value": np.asarray(values, dtype="float64")})


def test_lagged_exog_takes_previous_month_even_before_sales_start():
    ext_months = pd.period_range("2014-12", "2015-06", freq="M")
    external = external_frame(ext_months, range(len(ext_months)))  # 2014-12 → 0, 2015-01 → 1…
    X = lagged_exog(external, pd.period_range("2015-01", "2015-06", freq="M"))
    assert list(X.columns) == ["syndromes_grippaux"]
    assert X["syndromes_grippaux"].tolist() == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


def test_lagged_exog_refuses_missing_months():
    external = external_frame(pd.period_range("2015-01", "2015-03", freq="M"), [1, 2, 3])
    with pytest.raises(ValueError, match="2015-01"):
        lagged_exog(external, pd.period_range("2015-01", "2015-03", freq="M"))


def test_external_effect_on_seasonal_anomalies():
    months = pd.period_range("2015-01", periods=36, freq="M")
    season = np.tile(np.arange(12, dtype="float64"), 3)
    surprise = np.random.default_rng(0).normal(0, 1, 36)
    external = external_frame(months, 100 * season + surprise)
    monthly = pd.DataFrame({"N02BE": 5 * season + 3 * surprise,           # suit les surprises
                            "R06": 5 * season + np.random.default_rng(1).normal(0, 1, 36)},  # hiver seul
                           index=months)
    results = pd.DataFrame({"atc": ["N02BE", "N02BE", "R06", "R06"], "model": ["sarima", "sarimax"] * 2,
                            "mase": [0.8, 0.6, 1.0, 1.1]})
    out = external_effect(monthly, external, results).set_index("atc")
    assert list(external_effect(monthly, external, results).columns) == EFFECT_COLUMNS
    assert out.loc["N02BE", "corr"] == pytest.approx(1.0)
    assert abs(out.loc["R06", "corr"]) < 0.5  # la saisonnalité commune seule ne crée pas de corrélation
    assert out.loc["N02BE", "delta_mase"] == pytest.approx(-0.2)
    assert out.loc["R06", "delta_mase"] == pytest.approx(0.1)
