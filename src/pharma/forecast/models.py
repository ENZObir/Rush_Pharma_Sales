"""Modèles : ETS, SARIMA, régression avec variable exogène. Même interface que les baselines."""

from typing import Protocol

import pandas as pd


class Forecaster(Protocol):
    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "Forecaster": ...
    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series: ...


class ETS:
    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "ETS":
        raise NotImplementedError

    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series:
        raise NotImplementedError


class SARIMA:
    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "SARIMA":
        raise NotImplementedError

    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series:
        raise NotImplementedError


class ExogRegression:
    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "ExogRegression":
        raise NotImplementedError

    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series:
        raise NotImplementedError
