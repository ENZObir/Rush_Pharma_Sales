"""Normalisation des colonnes, dtypes et parsing des dates (un parseur par source, ARCHITECTURE §4)."""

import pandas as pd

DROPPED_COLUMNS = ["Year", "Month", "Hour", "Weekday Name"]


def parse_dates(raw: pd.DataFrame, fmt: str) -> pd.Series:
    """Parse `datum` avec un format explicite (m/d/Y sauf Monthly) : aucune inférence."""
    return pd.to_datetime(raw["datum"], format=fmt)


def normalize(raw: pd.DataFrame, source: str, fmt: str) -> pd.DataFrame:
    """Supprime les colonnes dérivées, parse les dates, applique les dtypes.

    Sortie (format large) : date, hour, puis une colonne float64 par ATC.
    `hour` n'est renseigné que pour l'horaire ; `date` est ramenée à minuit.
    """
    df = raw.drop(columns=DROPPED_COLUMNS, errors="ignore")
    timestamps = parse_dates(df, fmt)
    df = df.drop(columns="datum")
    atc_columns = list(df.columns)

    df[atc_columns] = df[atc_columns].astype("float64")
    df.insert(0, "date", timestamps.dt.normalize())
    hour = timestamps.dt.hour if source == "hourly" else pd.NA
    df.insert(1, "hour", pd.Series(hour, index=df.index, dtype="Int8"))
    return df
