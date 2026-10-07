"""Contrôles de cohérence. Chaque fonction renvoie un DataFrame des lignes en cause."""

import pandas as pd


def missing_days(long_df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def duplicates(long_df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def negatives(long_df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def non_integers(long_df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def month_coverage(long_df: pd.DataFrame, source: str = "daily") -> pd.DataFrame:
   
    days = pd.Series(long_df.loc[long_df["source"] == source, "date"].unique())
    if days.empty:
        raise ValueError(f"aucune ligne pour la source {source!r}")

    coverage = (
        days.groupby(days.dt.to_period("M"))
        .nunique()
        .rename("days_present")
        .rename_axis("month")
        .reset_index()
    )
    coverage["days_in_month"] = coverage["month"].dt.days_in_month
    coverage["ratio"] = coverage["days_present"] / coverage["days_in_month"]
    return coverage


def last_complete_month(long_df: pd.DataFrame, min_ratio: float) -> pd.Period:
    """Dernier mois dont la couverture en jours ≥ min_ratio. Contrat A → B."""
    coverage = month_coverage(long_df)
    complete = coverage.loc[coverage["ratio"] >= min_ratio, "month"]
    if complete.empty:
        raise ValueError(f"aucun mois couvert à {min_ratio:.0%} ou plus")
    return complete.max()
