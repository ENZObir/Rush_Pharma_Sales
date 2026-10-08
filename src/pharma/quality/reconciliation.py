"""Réagrégation hourly → daily → weekly → monthly et comparaison aux fichiers fournis."""

import pandas as pd


def reconcile(long_df: pd.DataFrame, finer: str, coarser: str) -> pd.DataFrame:
    """Écarts par atc × période : colonnes period, atc, expected, actual, abs_gap, rel_gap."""
    long_df.groupby([""])
    return 


def reconcile_all(long_df: pd.DataFrame) -> pd.DataFrame:
    """Enchaîne toutes les comparaisons de granularité."""
    raise NotImplementedError
