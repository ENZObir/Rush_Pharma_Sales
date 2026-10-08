from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pharma.features.aggregate import aggregate
from pharma.forecast.backtest import BACKTEST_COLUMNS, rolling_origin, run_backtests, score, to_wide
from pharma.forecast.baselines import Naive, SeasonalNaive, future_index
from pharma.forecast.exogenous import lagged_exog

N_TEST = 12


class Spy:
    """Modèle espion : note les mois vus au fit et au predict, prévoit 0."""

    def __init__(self, log: list):
        self.log = log

    def fit(self, y, X=None):
        self.index_ = y.index
        self.seen = {"y_max": y.index.max(), "X_max": None if X is None else X.index.max(),
                     "X_values": None if X is None else X.to_numpy().ravel(), "model": self}
        self.log.append(self.seen)
        return self

    def predict(self, h, X=None):
        self.seen["X_future"] = None if X is None else list(X.index)
        self.seen["X_future_values"] = None if X is None else X.to_numpy().ravel()
        return pd.Series(0.0, index=future_index(self.index_, h))


@pytest.fixture
def y():
    return pd.Series(np.arange(48, dtype="float64"), index=pd.period_range("2015-01", periods=48, freq="M"))


@pytest.fixture
def X(y):
    return pd.DataFrame({"x": np.arange(len(y), dtype="float64")}, index=y.index)


def test_no_leakage(y, X):
    """Pour chaque origine : max(mois vus au fit, y ET X) < mois prévu."""
    log = []
    preds = rolling_origin(y, lambda: Spy(log), N_TEST, X)
    targets = list(y.index[-N_TEST:])
    assert preds["target"].tolist() == targets
    assert len(log) == N_TEST
    for seen, target in zip(log, targets):
        assert seen["y_max"] < target
        assert seen["X_max"] < target
        assert seen["X_future"] == [target]  # seule la ligne du mois prévu, X étant déjà décalé
    assert (preds["train_end"] < preds["target"]).all()


def test_no_leakage_of_external_values(y):
    """Chaque valeur externe vaut le numéro de son mois d'observation : aucune ne doit dater de M ou après."""
    months = pd.period_range(y.index[0] - 6, y.index[-1], freq="M")
    external = pd.DataFrame({"month": months, "variable": "syndromes_grippaux",
                             "value": [float(m.ordinal) for m in months]})
    log = []
    rolling_origin(y, lambda: Spy(log), N_TEST, lagged_exog(external, y.index))
    for seen, target in zip(log, y.index[-N_TEST:]):
        assert seen["X_values"].max() < target.ordinal
        assert seen["X_future_values"].tolist() == [(target - 1).ordinal]  # l'incidence de M-1, rien de plus


def test_no_leakage_two_steps_ahead(y, X):
    log = []
    rolling_origin(y, lambda: Spy(log), N_TEST, X, h=2)
    for seen, target in zip(log, y.index[-N_TEST:]):
        assert seen["y_max"] == target - 2
        assert seen["X_max"] == target - 2
        assert seen["X_future"] == [target - 1, target]


def test_new_model_for_each_origin(y):
    log = []
    rolling_origin(y, lambda: Spy(log), N_TEST)
    assert len({id(seen["model"]) for seen in log}) == N_TEST


def test_seasonal_naive_is_exact_on_a_periodic_series():
    index = pd.period_range("2015-01", periods=48, freq="M")
    monthly = pd.DataFrame({"R06": np.tile(np.arange(12, dtype="float64"), 4)}, index=index)
    preds = run_backtests(monthly, {"naive": Naive, "seasonal_naive": SeasonalNaive}, N_TEST)
    results = score(preds, monthly)
    assert list(results.columns) == BACKTEST_COLUMNS
    results = results.set_index("model")
    assert results.loc["seasonal_naive", "mae"] == 0
    assert results.loc["naive", "mae"] > 0


def test_score_by_hand():
    targets = pd.period_range("2019-01", periods=2, freq="M")
    monthly = pd.DataFrame({"N02BE": [10.0, 20.0, 14.0, 26.0, 30.0, 40.0]},
                           index=pd.period_range("2018-09", periods=6, freq="M"))
    preds = pd.DataFrame({
        "atc": "N02BE",
        "model": ["naive", "naive", "seasonal_naive", "seasonal_naive", "ets", "ets"],
        "target": list(targets) * 3,
        "y_true": [30.0, 40.0] * 3,
        "y_pred": [20.0, 30.0, 10.0, 20.0, 28.0, 41.0],
    })
    results = score(preds, monthly, period=2).set_index("model")
    # MAE : naive 10, seasonal_naive 20, ets 1.5
    assert results["mae"].to_dict() == {"naive": 10.0, "seasonal_naive": 20.0, "ets": 1.5}
    # échelle MASE sur l'historique avant 2019-01 seulement, à 2 périodes : (|14-10| + |26-20|) / 2 = 5
    assert results.loc["ets", "mase"] == pytest.approx(1.5 / 5)
    assert results.loc["naive", "mase"] == pytest.approx(10 / 5)
    # gain contre la MEILLEURE baseline (naive, MAE 10)
    assert results.loc["ets", "gain_vs_baseline"] == pytest.approx(1 - 1.5 / 10)
    assert results.loc["seasonal_naive", "gain_vs_baseline"] == pytest.approx(-1.0)


def test_to_wide_refuses_mixed_sources(real_long):
    with pytest.raises(ValueError, match="une seule source"):
        to_wide(aggregate(real_long, "M"))


def test_to_wide_on_daily_source(real_long, real_settings):
    wide = to_wide(aggregate(real_long[real_long["source"] == "daily"], "M"))
    assert list(wide.columns) == real_settings.atc_groups
    assert isinstance(wide.index, pd.PeriodIndex) and wide.index.freqstr == "M"
    assert wide.index.is_monotonic_increasing and wide.index.is_unique


def test_no_random_cross_validation_in_forecast_code():
    forbidden = ("KFold", "train_test_split", "shuffle", "cross_val", "sample(")
    for path in (Path(__file__).resolve().parents[1] / "src" / "pharma" / "forecast").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not [word for word in forbidden if word in text], path.name
