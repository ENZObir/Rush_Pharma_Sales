"""Dimensions temporelles dérivées de `date` (jamais lues dans les CSV)."""

import pandas as pd


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute year, month, iso_week, weekday, month_period."""
    raise NotImplementedError
