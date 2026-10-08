"""Variable externe dans la prévision : décalage anti-fuite et mesure de son apport."""

import pandas as pd

EFFECT_COLUMNS = ["atc", "variable", "corr", "delta_mase"]


def lagged_exog(external: pd.DataFrame, months: pd.PeriodIndex, lag: int = 1) -> pd.DataFrame:
    """Une colonne par variable externe, sur `months` : la valeur du mois M est celle observée en M − lag.

    Au moment de prévoir M, l'incidence n'est connue que jusqu'à M − 1 : prendre
    celle de M serait une fuite. Le décalage se fait sur la série externe complète,
    donc le premier mois de ventes reçoit bien la valeur du mois qui le précède.
    """
    wide = external.pivot(index="month", columns="variable", values="value")
    span = pd.period_range(min(wide.index.min(), months.min()), max(wide.index.max(), months.max()), freq="M")
    out = wide.reindex(span).shift(lag).reindex(months)
    if out.isna().any().any():
        missing = out.index[out.isna().any(axis=1)]
        raise ValueError(f"donnée externe absente pour {missing[0]} … {missing[-1]} (décalage de {lag} mois)")
    out.columns.name = None
    return out


def external_effect(monthly: pd.DataFrame, external: pd.DataFrame, results: pd.DataFrame,
                    period: int = 12, with_exog: str = "sarimax", without_exog: str = "sarima") -> pd.DataFrame:
    """external_effect (contrat B → A) : atc, variable, corr, delta_mase.

    - corr : corrélation entre écarts saisonniers (valeur − même mois l'an passé) des
      ventes et de la variable du MÊME mois. Sur les séries brutes, l'hiver commun
      suffirait à créer une corrélation ; les écarts à l'an passé ne gardent que les surprises.
    - delta_mase : MASE(SARIMA + variables décalées) − MASE(SARIMA), même backtest.
      Négatif = la variable améliore la prévision. Toutes les variables entrent
      ensemble dans SarimaX : avec plusieurs variables, c'est leur apport commun.
    """
    wide = external.pivot(index="month", columns="variable", values="value").reindex(monthly.index)
    mase = results.pivot(index="atc", columns="model", values="mase")
    delta = mase[with_exog] - mase[without_exog]
    rows = [{"atc": atc, "variable": variable,
             "corr": monthly[atc].diff(period).corr(wide[variable].diff(period)),
             "delta_mase": delta[atc]}
            for variable in wide.columns for atc in monthly.columns]
    return pd.DataFrame(rows, columns=EFFECT_COLUMNS)
