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


def last_complete_month(long_df: pd.DataFrame, min_ratio: float) -> pd.Period:
    """Dernier mois dont la couverture en jours ≥ min_ratio. Contrat A → B."""
    raise NotImplementedError
