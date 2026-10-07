"""Baselines naïves : M = M-1, et M = même mois l'an passé."""

import pandas as pd


class Naive:
    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "Naive":
        raise NotImplementedError

    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series:
        raise NotImplementedError


class SeasonalNaive:
    def __init__(self, period: int = 12):
        self.period = period

    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "SeasonalNaive":
        raise NotImplementedError

    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series:
        raise NotImplementedError
