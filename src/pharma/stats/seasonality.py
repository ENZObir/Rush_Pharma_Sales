"""Profils mensuel / jour / heure et indices saisonniers."""

import pandas as pd

PROFILE_COLUMNS = ["atc", "dimension", "key", "index"]


def seasonal_profile(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """dimension ∈ {"month", "weekday", "hour"}. Sortie : PROFILE_COLUMNS. Contrat B → A."""
    raise NotImplementedError
