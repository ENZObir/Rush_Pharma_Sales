"""Baselines naïves : M = M-1, et M = même mois l'an passé.

Séries mensuelles indexées par un PeriodIndex : la prévision est indexée par les
h mois qui suivent le dernier mois vu au fit.
"""

import numpy as np
import pandas as pd


def future_index(index: pd.PeriodIndex, h: int) -> pd.PeriodIndex:
    """Les h périodes qui suivent la dernière de `index`."""
    if not isinstance(index, pd.PeriodIndex):
        raise TypeError(f"PeriodIndex attendu, reçu {type(index).__name__}")
    return pd.period_range(index[-1] + 1, periods=h, freq=index.freq)


class Naive:
    """M = M-1 : la dernière valeur observée est répétée."""

    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "Naive":
        self.last_ = float(y.iloc[-1])
        self.index_ = y.index
        return self

    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series:
        return pd.Series(self.last_, index=future_index(self.index_, h))


class SeasonalNaive:
    """M = M - period : le dernier cycle observé est répété."""

    def __init__(self, period: int = 12):
        self.period = period

    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "SeasonalNaive":
        if len(y) < self.period:
            raise ValueError(f"au moins {self.period} points requis, reçu {len(y)}")
        self.season_ = y.iloc[-self.period:].to_numpy(dtype="float64")
        self.index_ = y.index
        return self

    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series:
        return pd.Series(np.resize(self.season_, h), index=future_index(self.index_, h))
