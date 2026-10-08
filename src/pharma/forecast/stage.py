"""Étape forecast : du format long aux 5 DataFrames du contrat B → A (ARCHITECTURE §7.2).

Fonction pure : la donnée externe est chargée par l'appelant (`io.external.load_external`)
et passée en argument ; rien n'est lu ni écrit ici.
"""

from dataclasses import dataclass
from functools import partial

import pandas as pd

from pharma.config import Settings
from pharma.features.aggregate import aggregate
from pharma.forecast.backtest import BASELINES, run_backtests, score, to_wide
from pharma.forecast.baselines import Naive, SeasonalNaive
from pharma.forecast.exogenous import EFFECT_COLUMNS, external_effect, lagged_exog
from pharma.forecast.models import ETS, SARIMA, SarimaX
from pharma.quality.checks import last_complete_month
from pharma.stats.seasonality import seasonal_profile
from pharma.stats.variability import variability

CHOICE_COLUMNS = ["atc", "model", "verdict"]
FORECAST_COLUMNS = ["atc", "month", "yhat", "model", "verdict"]


def candidate_models(period: int = 12) -> dict:
    """Modèles en compétition pour la prévision (SarimaX ne sert qu'à mesurer l'apport externe)."""
    return {
        "naive": Naive,
        "seasonal_naive": partial(SeasonalNaive, period),
        "ets": partial(ETS, period),
        "sarima": partial(SARIMA, period),
    }


def choose_models(results: pd.DataFrame, min_gain: float,
                  candidates: list[str], baselines: tuple[str, ...] = BASELINES) -> pd.DataFrame:
    """Modèle retenu et verdict par ATC.

    Meilleur modèle = MASE minimale parmi `candidates` (même échelle par ATC, donc
    même classement que la MAE). « oui » s'il n'est pas une baseline ET bat la
    meilleure baseline d'au moins `min_gain` ; sinon « non » et on retient la
    meilleure baseline : un modèle qui ne fait pas mieux que le naïf ne se vend pas.
    """
    rows = []
    for atc, r in results[results["model"].isin(candidates)].groupby("atc", sort=False):
        r = r.set_index("model")
        best = r["mae"].idxmin()
        if best not in baselines and r.loc[best, "gain_vs_baseline"] >= min_gain:
            rows.append({"atc": atc, "model": best, "verdict": "oui"})
        else:
            rows.append({"atc": atc, "model": r.loc[list(baselines), "mae"].idxmin(), "verdict": "non"})
    return pd.DataFrame(rows, columns=CHOICE_COLUMNS)


@dataclass
class ForecastStage:
    """Les 5 sorties du contrat, plus le détail utile aux figures."""

    seasonal_profile: pd.DataFrame
    variability: pd.DataFrame
    backtest_results: pd.DataFrame
    forecast_next: pd.DataFrame
    external_effect: pd.DataFrame
    monthly: pd.DataFrame          # ventes mensuelles, mois complets, une colonne par ATC
    predictions: pd.DataFrame      # détail du backtest (atc, model, target, y_true, y_pred…)
    external: pd.DataFrame
    last_complete_month: pd.Period

    def outputs(self) -> dict[str, pd.DataFrame]:
        return {"seasonal_profile": self.seasonal_profile, "variability": self.variability,
                "backtest_results": self.backtest_results, "forecast_next": self.forecast_next,
                "external_effect": self.external_effect}


def compute_forecast_stage(settings: Settings, long_df: pd.DataFrame,
                           external: pd.DataFrame | None = None) -> ForecastStage:
    cfg = settings.forecast
    period, h = cfg["seasonal_period"], cfg["horizon"]
    last = last_complete_month(long_df, settings.quality["incomplete_month_ratio"])
    in_scope = long_df["date"] <= last.to_timestamp(how="end")  # le mois incomplet ne sert nulle part
    daily = long_df[in_scope & (long_df["source"] == "daily")]
    hourly = long_df[in_scope & (long_df["source"] == "hourly")]
    monthly_long = aggregate(daily, "M")
    monthly = to_wide(monthly_long)

    profile = pd.concat([seasonal_profile(monthly_long, "month"), seasonal_profile(daily, "weekday"),
                         seasonal_profile(hourly, "hour")], ignore_index=True)

    models = candidate_models(period)
    use_exog = external is not None and not external.empty
    X = None
    if use_exog:
        models["sarimax"] = partial(SarimaX, period)
        X = lagged_exog(external, monthly.index, lag=h)
    predictions = run_backtests(monthly, models, cfg["backtest_months"], X, h)
    results = score(predictions, monthly, period)

    choice = choose_models(results, cfg["verdict_min_gain"], list(candidate_models(period)))
    rows = []
    for atc, name, verdict in choice.itertuples(index=False):
        yhat = models[name]().fit(monthly[atc]).predict(h)  # réentraîné sur tout l'historique complet
        rows.append({"atc": atc, "month": str(yhat.index[-1]), "yhat": float(yhat.iloc[-1]),
                     "model": name, "verdict": verdict})
    forecast_next = pd.DataFrame(rows, columns=FORECAST_COLUMNS)

    retained = predictions.merge(choice[["atc", "model"]], on=["atc", "model"])
    errors = retained.assign(error=retained["y_true"] - retained["y_pred"])[["atc", "error"]]
    var = variability(monthly, errors, cfg["service_level_z"], cfg["lead_time_months"])

    effect = (external_effect(monthly, external, results, period) if use_exog
              else pd.DataFrame(columns=EFFECT_COLUMNS))
    return ForecastStage(profile, var, results, forecast_next, effect,
                         monthly, predictions, external, last)


def run_forecast_stage(settings: Settings, long_df: pd.DataFrame,
                       external: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Contrat B → A : seasonal_profile, variability, backtest_results, forecast_next, external_effect."""
    return compute_forecast_stage(settings, long_df, external).outputs()
