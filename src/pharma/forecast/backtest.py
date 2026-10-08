"""Backtest à origine glissante : le mois M est prévu avec les données jusqu'à M-1 seulement.

Aucune validation croisée aléatoire : pour une prévision, seule une découpe dans
l'ordre du temps est honnête, sinon des mois futurs se retrouvent dans l'entraînement.
"""

from collections.abc import Callable

import pandas as pd

from pharma.forecast.metrics import gain_vs_baseline, mae, mape, mase
from pharma.forecast.models import Forecaster

PREDICTION_COLUMNS = ["origin", "target", "y_true", "y_pred", "train_end", "fallback"]
BACKTEST_COLUMNS = ["atc", "model", "mae", "mape", "mase", "gain_vs_baseline"]
BASELINES = ("naive", "seasonal_naive")


def to_wide(df_agg: pd.DataFrame) -> pd.DataFrame:
    """Sortie mensuelle de `aggregate` → une colonne par ATC, index mensuel continu (PeriodIndex).

    Une seule source acceptée : additionner daily + hourly + … compterait chaque
    vente plusieurs fois. Filtrer `source` avant d'appeler.
    """
    sources = df_agg["source"].astype(str).unique()
    if len(sources) != 1:
        raise ValueError(f"une seule source attendue, reçu {sorted(sources)} : filtrer `source` avant")
    # atc en str : une catégorie absente des données ne doit pas créer de colonne vide
    wide = df_agg.assign(atc=df_agg["atc"].astype(str)).pivot(index="date", columns="atc", values="quantity")
    wide.index = wide.index.to_period("M").rename("month")
    full = pd.period_range(wide.index.min(), wide.index.max(), freq="M")
    if len(full) != len(wide) or wide.isna().any().any():
        raise ValueError(f"série mensuelle incomplète entre {full[0]} et {full[-1]}")
    return wide


def rolling_origin(y: pd.Series, make_model: Callable[[], Forecaster], n_test: int,
                   X: pd.DataFrame | None = None, h: int = 1) -> pd.DataFrame:
    """Prévoit chacun des `n_test` derniers mois de y, à h pas, depuis son origine M-h.

    Pour chaque cible M : modèle neuf, entraîné sur y et X restreints aux mois ≤ M-h,
    puis `predict(h, X des mois M-h+1 … M)`. X doit donc être déjà décalé d'au moins
    h mois (la valeur de X au mois M doit être connue en M-h).
    Colonnes : PREDICTION_COLUMNS ; `fallback` = le modèle s'est replié sur une baseline.
    """
    if not 0 < n_test < len(y):
        raise ValueError(f"n_test doit être entre 1 et {len(y) - 1}, reçu {n_test}")
    rows = []
    for target in y.index[-n_test:]:
        origin = target - h
        y_train = y[y.index <= origin]
        X_train = None if X is None else X.loc[y_train.index]
        X_future = None if X is None else X.loc[origin + 1:target]
        model = make_model().fit(y_train, X_train)
        pred = model.predict(h, X_future)
        if pred.index[-1] != target:
            raise RuntimeError(f"prévision indexée {pred.index[-1]}, cible {target}")
        rows.append({
            "origin": origin,
            "target": target,
            "y_true": float(y[target]),
            "y_pred": float(pred.iloc[-1]),
            "train_end": y_train.index.max(),
            "fallback": bool(getattr(model, "fallback_", False)),
        })
    return pd.DataFrame(rows, columns=PREDICTION_COLUMNS)


def run_backtests(monthly: pd.DataFrame, models: dict[str, Callable[[], Forecaster]],
                  n_test: int, X: pd.DataFrame | None = None, h: int = 1) -> pd.DataFrame:
    """`rolling_origin` pour chaque ATC (colonne de `monthly`, cf. `to_wide`) × modèle.

    Colonnes : atc, model, puis PREDICTION_COLUMNS. Entrée de `score`.
    """
    frames = []
    for atc in monthly.columns:
        for name, make_model in models.items():
            preds = rolling_origin(monthly[atc], make_model, n_test, X, h)
            frames.append(preds.assign(atc=atc, model=name))
    out = pd.concat(frames, ignore_index=True)
    return out[["atc", "model", *PREDICTION_COLUMNS]]


def score(predictions: pd.DataFrame, monthly: pd.DataFrame, period: int = 12,
          baselines: tuple[str, ...] = BASELINES) -> pd.DataFrame:
    """backtest_results (contrat B → A) : atc, model, mae, mape, mase, gain_vs_baseline.

    - échelle MASE : naïf saisonnier sur l'historique de l'ATC AVANT le 1ᵉʳ mois testé ;
    - gain_vs_baseline : 1 − MAE du modèle / MAE de la MEILLEURE baseline de l'ATC.
    """
    if not set(baselines) & set(predictions["model"]):
        raise ValueError(f"aucune baseline {baselines} dans les prédictions")
    rows = []
    for atc, by_atc in predictions.groupby("atc", sort=False):
        history = monthly.loc[monthly.index < by_atc["target"].min(), atc]
        scores = {}
        for name, preds in by_atc.groupby("model", sort=False):
            y_true = preds.set_index("target")["y_true"]
            y_pred = preds.set_index("target")["y_pred"]
            scores[name] = {"mae": mae(y_true, y_pred), "mape": mape(y_true, y_pred),
                            "mase": mase(y_true, y_pred, history, period)}
        best_baseline = min(s["mae"] for name, s in scores.items() if name in baselines)
        for name, s in scores.items():
            rows.append({"atc": atc, "model": name, **s,
                         "gain_vs_baseline": gain_vs_baseline(s["mae"], best_baseline)})
    return pd.DataFrame(rows, columns=BACKTEST_COLUMNS)
