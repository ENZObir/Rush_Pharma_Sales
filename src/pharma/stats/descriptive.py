"""Volumes, parts et tendance pluriannuelle par groupe ATC.

Entrée : ventes mensuelles au format long (`aggregate(..., "M")`), mois complets uniquement.
"""

import pandas as pd

from pharma.features.aggregate import aggregate

VOLUME_COLUMNS = ["atc", "total", "share", "monthly_mean", "months"]
TREND_COLUMNS = ["atc", "year", "months", "total", "monthly_mean", "growth_same_months"]


def monthly_sales(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Ventes mensuelles recalculées depuis le journalier, mois complets uniquement."""
    daily = clean_df[(clean_df["source"] == "daily") & clean_df["complete_month"]]
    return aggregate(daily, "M")


def volumes_and_shares(monthly: pd.DataFrame) -> pd.DataFrame:
    """Volume total, part du total, moyenne mensuelle et nombre de mois par ATC, du plus gros au plus petit."""
    out = (
        monthly.groupby("atc", observed=True)["quantity"]
        .agg(total="sum", monthly_mean="mean", months="count")
        .reset_index()
    )
    out["share"] = out["total"] / out["total"].sum()
    return out.sort_values("total", ascending=False, ignore_index=True)[VOLUME_COLUMNS]


def yearly_trend(monthly: pd.DataFrame) -> pd.DataFrame:
    """Total annuel par ATC et évolution vs l'année précédente **sur les mêmes mois**.

    Comparer à mois identiques évite qu'une année partielle (ex. 9 mois) paraisse en baisse
    ou qu'une saisonnalité forte fausse l'évolution.
    """
    df = monthly.assign(year=monthly["date"].dt.year, month=monthly["date"].dt.month)
    rows = []
    for (atc, year), g in df.groupby(["atc", "year"], observed=True):
        prev = df[(df["atc"] == atc) & (df["year"] == year - 1) & df["month"].isin(g["month"])]
        same_months = prev["month"].nunique() == g["month"].nunique()
        growth = g["quantity"].sum() / prev["quantity"].sum() - 1 if same_months and len(prev) else float("nan")
        rows.append({"atc": atc, "year": year, "months": g["month"].nunique(), "total": g["quantity"].sum(),
                     "monthly_mean": g["quantity"].mean(), "growth_same_months": growth})
    out = pd.DataFrame(rows, columns=TREND_COLUMNS)
    out["atc"] = out["atc"].astype(monthly["atc"].dtype)
    return out
