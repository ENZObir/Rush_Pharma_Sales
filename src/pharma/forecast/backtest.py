"""Backtest à origine glissante : le mois M est prévu avec les données jusqu'à M-1 seulement."""

from collections.abc import Callable

import pandas as pd

from pharma.forecast.models import Forecaster


def rolling_origin(y: pd.Series, make_model: Callable[[], Forecaster], n_test: int,
                   X: pd.DataFrame | None = None, h: int = 1) -> pd.DataFrame:
    """Colonnes : origin, target, y_true, y_pred, train_end."""
    raise NotImplementedError


def run_backtests(monthly: pd.DataFrame, models: dict[str, Callable[[], Forecaster]],
                  n_test: int, X: pd.DataFrame | None = None) -> pd.DataFrame:
    """backtest_results (contrat B → A) : atc, model, mae, mape, mase, gain_vs_baseline."""
    raise NotImplementedError
