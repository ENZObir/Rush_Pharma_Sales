"""Coefficient de variation et stock de sécurité."""

import pandas as pd

VARIABILITY_COLUMNS = ["atc", "cv", "safety_stock"]


def variability(monthly: pd.DataFrame, forecast_errors: pd.DataFrame | None = None) -> pd.DataFrame:
    """Sortie : VARIABILITY_COLUMNS. Contrat B → A."""
    raise NotImplementedError
