"""MAE, MAPE, MASE et gain relatif par rapport à la baseline."""

import pandas as pd


def mae(y_true: pd.Series, y_pred: pd.Series) -> float:
    raise NotImplementedError


def mape(y_true: pd.Series, y_pred: pd.Series) -> float:
    raise NotImplementedError


def mase(y_true: pd.Series, y_pred: pd.Series, y_train: pd.Series, period: int = 1) -> float:
    raise NotImplementedError


def gain_vs_baseline(model_error: float, baseline_error: float) -> float:
    raise NotImplementedError
