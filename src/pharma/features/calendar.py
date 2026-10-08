"""Dimensions temporelles dérivées de `date` (jamais lues dans les CSV)."""

import pandas as pd


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute year, month, iso_week, weekday (0 = lundi), month_period."""
    out = df.copy()
    dates = out["date"]
    out["year"] = dates.dt.year.astype("int16")
    out["month"] = dates.dt.month.astype("int8")
    out["iso_week"] = dates.dt.isocalendar().week.astype("int8")
    out["weekday"] = dates.dt.weekday.astype("int8")
    out["month_period"] = dates.dt.to_period("M")
    return out
