"""Contrôles de cohérence. Chaque fonction renvoie un DataFrame des lignes en cause."""

import pandas as pd

KEY = ["date", "hour", "atc", "source"]

# Pas attendu entre deux lignes consécutives de chaque export (mêmes étiquettes que features/aggregate.py).
EXPECTED_FREQ = {"hourly": "h", "daily": "D", "weekly": "W-SUN", "monthly": "ME"}

INTEGER_TOLERANCE = 1e-6


def _timestamps(df: pd.DataFrame) -> pd.Series:
    """date + heure pour l'horaire, date seule sinon."""
    return df["date"] + pd.to_timedelta(df["hour"].fillna(0).astype("int64"), unit="h")


def missing_days(long_df: pd.DataFrame) -> pd.DataFrame:
    """Périodes absentes entre la première et la dernière date de chaque source.

    Colonnes : source, date, hour. Une heure absente de l'horaire apparaît avec son heure ;
    les heures avant la 1ʳᵉ et après la dernière ligne ne sont pas comptées.
    """
    missing = []
    for source, group in long_df.groupby("source", observed=True):
        present = pd.DatetimeIndex(_timestamps(group).unique())
        expected = pd.date_range(present.min(), present.max(), freq=EXPECTED_FREQ[source])
        absent = expected.difference(present)
        missing.append(pd.DataFrame({
            "source": source,
            "date": absent.normalize(),
            "hour": pd.array(absent.hour if source == "hourly" else [pd.NA] * len(absent), dtype="Int8"),
        }))
    return pd.concat(missing, ignore_index=True)


def duplicates(long_df: pd.DataFrame) -> pd.DataFrame:
    """Toutes les lignes dont la clé date × hour × atc × source apparaît plusieurs fois."""
    return long_df[long_df.duplicated(KEY, keep=False)].sort_values(KEY)


def negatives(long_df: pd.DataFrame) -> pd.DataFrame:
    """Lignes à quantité strictement négative."""
    return long_df[long_df["quantity"] < 0]


def non_integers(long_df: pd.DataFrame) -> pd.DataFrame:
    """Lignes à quantité non entière (au-delà du bruit d'arrondi des flottants).

    Constat à signaler, pas à corriger : l'unité n'est pas documentée.
    """
    q = long_df["quantity"]
    return long_df[(q - q.round()).abs() > INTEGER_TOLERANCE]


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
