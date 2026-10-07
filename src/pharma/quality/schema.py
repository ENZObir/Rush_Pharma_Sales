"""Normalisation des colonnes, dtypes et parsing des dates (un parseur par source, ARCHITECTURE §4)."""

import pandas as pd

DROPPED_COLUMNS = ["Year", "Month", "Hour", "Weekday Name"]


def parse_dates(raw: pd.DataFrame, fmt: str) -> pd.Series:
    """Parse `datum` avec un format explicite (m/d/Y sauf Monthly)."""
    raise NotImplementedError


def normalize(raw: pd.DataFrame, source: str, fmt: str) -> pd.DataFrame:
    """Supprime les colonnes dérivées, parse les dates, applique les dtypes."""
    raise NotImplementedError
