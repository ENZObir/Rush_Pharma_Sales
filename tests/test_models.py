import warnings

import numpy as np
import pandas as pd
import pytest
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from pharma.forecast.baselines import SeasonalNaive
from pharma.forecast.models import ETS, SARIMA, SarimaX

INDEX = pd.period_range("2014-01", periods=60, freq="M")
SEASON = 50 * np.sin(2 * np.pi * np.arange(60) / 12)


@pytest.fixture
def y():
    noise = np.random.default_rng(0).normal(0, 3, 60)
    return pd.Series(200 + np.arange(60) + SEASON + noise, index=INDEX)


@pytest.fixture
def X():
    return pd.DataFrame({"x": np.random.default_rng(1).gamma(2, 50, 61)},
                        index=pd.period_range("2014-01", periods=61, freq="M"))


@pytest.mark.parametrize("model", [ETS, SARIMA])
def test_forecasts_following_months_without_fallback(model, y):
    m = model().fit(y)
    pred = m.predict(3)
    assert pred.index.tolist() == list(pd.period_range("2019-01", periods=3, freq="M"))
    assert np.isfinite(pred).all()
    assert not m.fallback_
    truth = 200 + np.arange(60, 63) + 50 * np.sin(2 * np.pi * np.arange(60, 63) / 12)
    assert np.abs(pred.to_numpy() - truth).max() < 25


@pytest.mark.parametrize("model", [ETS, SARIMA])
def test_statsmodels_warnings_are_silenced(model, y):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        model().fit(y).predict(1)


def test_sarimax_uses_x(X):
    # marche aléatoire saisonnière (y_t = y_(t-12) + bruit) : le cas pour lequel SARIMA est conçu
    shocks = np.random.default_rng(2).normal(0, 10, 60)
    base = np.array([sum(shocks[t::-12]) for t in range(60)]) + 300
    y_exog = pd.Series(base + 2 * X["x"].iloc[:60].to_numpy(), index=INDEX)
    m = SarimaX().fit(y_exog, X.iloc[:60])
    low = m.predict(1, pd.DataFrame({"x": [0.0]}, index=X.index[60:]))
    high = m.predict(1, pd.DataFrame({"x": [100.0]}, index=X.index[60:]))
    assert not m.fallback_
    assert high.iloc[0] - low.iloc[0] == pytest.approx(200, rel=0.1)  # coefficient ≈ 2


def test_sarimax_refuses_missing_or_misaligned_x(y, X):
    with pytest.raises(ValueError, match="X requis"):
        SarimaX().fit(y)
    with pytest.raises(ValueError, match="X requis"):
        SarimaX().fit(y, X.iloc[1:61])
    with pytest.raises(ValueError, match="manquantes"):
        SarimaX().fit(y, X.iloc[:60].assign(x=np.nan))


def test_sarima_ignores_x(y, X):
    a = SARIMA().fit(y).predict(1)
    b = SARIMA().fit(y, X.iloc[:60]).predict(1, X.iloc[60:])
    assert a.equals(b)


def test_error_falls_back_to_seasonal_naive(y, monkeypatch):
    def broken(self, y, exog):
        raise np.linalg.LinAlgError("matrice singulière")

    monkeypatch.setattr(ETS, "_fit", broken)
    m = ETS().fit(y)
    assert m.fallback_ and "LinAlgError" in m.fallback_reason_
    assert m.predict(2).equals(SeasonalNaive().fit(y).predict(2))


def test_convergence_warning_falls_back(y, monkeypatch):
    def not_converged(self, y, exog):
        warnings.warn("pas de convergence", ConvergenceWarning)
        return None

    monkeypatch.setattr(SARIMA, "_fit", not_converged)
    m = SARIMA().fit(y)
    assert m.fallback_ and m.fallback_reason_ == "non-convergence"
    assert m.predict(1).equals(SeasonalNaive().fit(y).predict(1))
