"""Les 4 exports CSV → format long canonique (ARCHITECTURE §3). Seul module qui connaît la forme des CSV."""

import pandas as pd

from pharma.config import Settings

LONG_COLUMNS = ["date", "hour", "atc", "quantity", "source", "granularity"]


def load_source(settings: Settings, source: str) -> pd.DataFrame:
    """Charge un export (`hourly`/`daily`/`weekly`/`monthly`) au format long."""
    raise NotImplementedError


def load_all(settings: Settings) -> pd.DataFrame:
    """Concatène les 4 sources au format long. Contrat A → B."""
    raise NotImplementedError
