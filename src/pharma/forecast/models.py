"""Modèles : ETS, SARIMA et SARIMA avec variable exogène. Même interface que les baselines.

Si l'estimation échoue ou ne converge pas, le modèle se replie sur le naïf
saisonnier et le signale (`fallback_`, `fallback_reason_`) : le backtest compte
les replis au lieu de les cacher. Les avertissements statsmodels sont capturés
localement, jamais affichés.
"""

import warnings
from typing import Protocol

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from pharma.forecast.baselines import SeasonalNaive, future_index


class Forecaster(Protocol):
    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "Forecaster": ...
    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series: ...


class _StatsmodelsForecaster:
    """Socle commun : X validé, estimation silencieuse, repli sur SeasonalNaive."""

    uses_exog = False

    def __init__(self, period: int = 12):
        self.period = period

    def _fit(self, y: np.ndarray, exog: np.ndarray | None):
        raise NotImplementedError

    def _forecast(self, h: int, exog: np.ndarray | None) -> np.ndarray:
        raise NotImplementedError

    def _exog(self, X: pd.DataFrame | None, index: pd.PeriodIndex) -> np.ndarray | None:
        """X en matrice, seulement si le modèle l'utilise. Erreur explicite (pas de repli) si X est inexploitable."""
        if not self.uses_exog:
            return None
        if X is None or not X.index.equals(index):
            raise ValueError(f"{type(self).__name__} : X requis, indexé exactement comme {index[0]} … {index[-1]}")
        exog = X.to_numpy(dtype="float64")
        if not np.isfinite(exog).all():
            raise ValueError(f"{type(self).__name__} : X contient des valeurs manquantes")
        return exog

    def fit(self, y: pd.Series, X: pd.DataFrame | None = None):
        self.index_ = y.index
        exog = self._exog(X, y.index)
        self.backup_ = SeasonalNaive(self.period).fit(y)
        self.fallback_, self.fallback_reason_ = False, None
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                # toute erreur numérique de statsmodels (LinAlgError, ValueError…) déclenche le repli
                self.result_ = self._fit(y.to_numpy(dtype="float64"), exog)
            except Exception as exc:
                self.fallback_, self.fallback_reason_ = True, f"{type(exc).__name__}: {exc}"
        if not self.fallback_ and any(issubclass(w.category, ConvergenceWarning) for w in caught):
            self.fallback_, self.fallback_reason_ = True, "non-convergence"
        return self

    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series:
        index = future_index(self.index_, h)
        if not self.fallback_:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                values = np.asarray(self._forecast(h, self._exog(X, index)), dtype="float64")
            if np.isfinite(values).all():
                return pd.Series(values, index=index)
            self.fallback_, self.fallback_reason_ = True, "prévision non finie"
        return self.backup_.predict(h)


class ETS(_StatsmodelsForecaster):
    """Holt-Winters : tendance additive amortie, saisonnalité additive de période 12.

    Amortie : on ne prolonge pas indéfiniment une pente estimée sur quelques années.
    """

    def _fit(self, y, exog):
        return ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="add",
                                    seasonal_periods=self.period, initialization_method="estimated").fit()

    def _forecast(self, h, exog):
        return self.result_.forecast(h)


class SARIMA(_StatsmodelsForecaster):
    """SARIMA (1,0,0)(0,1,1)12, ordre fixe pour tous les ATC (pas d'auto-ARIMA : sur-ajustement).

    Différence saisonnière (écart au même mois l'an passé), AR(1) sur cet écart,
    MA(1) saisonnier. Ignore X.
    """

    order = (1, 0, 0)
    seasonal_order = (0, 1, 1)

    def _fit(self, y, exog):
        result = SARIMAX(y, exog=exog, order=self.order,
                         seasonal_order=(*self.seasonal_order, self.period)).fit(disp=False)
        if not result.mle_retvals.get("converged", True):
            raise RuntimeError("non-convergence du maximum de vraisemblance")
        return result

    def _forecast(self, h, exog):
        return self.result_.forecast(h, exog=exog)


class SarimaX(SARIMA):
    """Même SARIMA + régresseurs exogènes X, qui doivent être connus au moment de prévoir (X décalé)."""

    uses_exog = True
