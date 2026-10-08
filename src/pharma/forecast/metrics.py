"""MAE, MAPE, MASE et gain relatif par rapport à la baseline.

Les erreurs se calculent sur les mois communs à y_true et y_pred (alignement par index).
"""

import pandas as pd


def _aligned(y_true: pd.Series, y_pred: pd.Series) -> tuple[pd.Series, pd.Series]:
    true, pred = y_true.astype("float64").align(y_pred.astype("float64"), join="inner")
    if true.empty:
        raise ValueError("aucune période commune entre y_true et y_pred")
    return true, pred


def mae(y_true: pd.Series, y_pred: pd.Series) -> float:
    true, pred = _aligned(y_true, y_pred)
    return float((true - pred).abs().mean())


def mape(y_true: pd.Series, y_pred: pd.Series) -> float:
    """Erreur absolue moyenne rapportée au réel, en fraction (0.12 = 12 %).

    Les mois à réel nul sont exclus (division impossible) ; NaN s'il n'en reste aucun.
    """
    true, pred = _aligned(y_true, y_pred)
    keep = true != 0
    if not keep.any():
        return float("nan")
    return float(((true[keep] - pred[keep]).abs() / true[keep].abs()).mean())


def mase_scale(y_train: pd.Series, period: int = 12) -> float:
    """MAE in-sample du naïf saisonnier : moyenne de |y_t − y_(t−period)| sur y_train.

    y_train = l'historique AVANT la fenêtre de test, pour que l'échelle ne voie
    aucun mois évalué.
    """
    diffs = y_train.astype("float64").diff(period).dropna()
    if diffs.empty:
        raise ValueError(f"plus de {period} points requis pour l'échelle MASE, reçu {len(y_train)}")
    return float(diffs.abs().mean())


def mase(y_true: pd.Series, y_pred: pd.Series, y_train: pd.Series, period: int = 12) -> float:
    """MAE / mase_scale(y_train). < 1 : plus précis que le naïf saisonnier in-sample.

    Une seule échelle par ATC pour tous les modèles : comparer leurs MASE revient
    à comparer leurs MAE, mais la MASE se compare aussi d'un ATC à l'autre.
    """
    scale = mase_scale(y_train, period)
    return mae(y_true, y_pred) / scale if scale > 0 else float("nan")


def gain_vs_baseline(model_error: float, baseline_error: float) -> float:
    """1 − erreur_modèle / erreur_baseline. 0.10 = 10 % d'erreur en moins ; < 0 = pire."""
    if baseline_error == 0:
        return float("nan")
    return 1.0 - model_error / baseline_error
