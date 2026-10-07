"""Récupération et cache des données publiques (Sentinelles, pollens, jours fériés…)."""

import pandas as pd

from pharma.config import Settings


def fetch(settings: Settings, name: str, use_network: bool = True) -> pd.DataFrame:
    """Lit data/external/<name>.csv ; le (re)télécharge si absent et use_network."""
    raise NotImplementedError


def load_external(settings: Settings, use_network: bool = True) -> pd.DataFrame:
    """Toutes les variables externes alignées sur `date`."""
    raise NotImplementedError
