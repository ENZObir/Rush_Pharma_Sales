"""Les 4 exports CSV → format long canonique (ARCHITECTURE §3). Seul module qui connaît la forme des CSV."""

import pandas as pd

from pharma.config import Settings

LONG_COLUMNS = ["date", "hour", "atc", "quantity", "source", "granularity"]


def load_source(settings: Settings, source: str) -> pd.DataFrame:
    """Charge un export (`hourly`/`daily`/`weekly`/`monthly`) au format long."""
    raise NotImplementedError


def load_all(settings: Settings) -> pd.DataFrame:
    """Concatène les 4 sources au format long. Contrat A → B."""
    raw = pd.read_csv(settings.raw_dir / settings.raw_files)
    df = raw.melt(id_vars= "datum", value_vars=settings.atc_groups,
    var_name="atc", value_name="quantity")
    df["date"] = pd.to_datetime(df["datum"], format=settings.date_formats["monthly"])
    df["hour"] = pd.array([pd.NA] * len(df), dtype="Int8")
    df["source"] = df["granularity"] = "monthly"
    
    raise NotImplementedError
