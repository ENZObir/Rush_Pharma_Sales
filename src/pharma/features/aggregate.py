"""Une seule fonction d'agrégation, paramétrée par granularité."""

import pandas as pd

GRANULARITIES = {"D": "D", "W": "W-SUN", "M": "MS"}


def aggregate(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    """Somme des quantités par atc × période. granularity ∈ {"D", "W", "M"}. Contrat A → B."""
    raise NotImplementedError
