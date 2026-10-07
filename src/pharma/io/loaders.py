"""Les 4 exports CSV → format long canonique (ARCHITECTURE §3). Seul module qui connaît la forme des CSV."""

import pandas as pd

from pharma.config import Settings
from pharma.quality.schema import normalize

LONG_COLUMNS = ["date", "hour", "atc", "quantity", "source", "granularity"]


def load_source(settings: Settings, source: str) -> pd.DataFrame:
    """Charge un export (`hourly`/`daily`/`weekly`/`monthly`) au format long."""
    raw = pd.read_csv(settings.raw_dir / settings.raw_files[source])
    wide = normalize(raw, source, settings.date_formats[source])

    missing = set(settings.atc_groups) - set(wide.columns)
    if missing:
        raise ValueError(f"{source} : groupes ATC absents du CSV : {sorted(missing)}")

    df = wide.melt(id_vars=["date", "hour"], value_vars=settings.atc_groups,
                   var_name="atc", value_name="quantity")
    df["source"] = source
    df["granularity"] = source
    return df[LONG_COLUMNS]


def load_all(settings: Settings) -> pd.DataFrame:
    """Empile les 4 sources au format long. Contrat A → B.

    Les sources sont des vues redondantes des mêmes ventes : toujours filtrer
    sur `source` avant d'agréger, ne jamais sommer toutes les lignes.
    """
    sources = list(settings.raw_files)
    df = pd.concat([load_source(settings, s) for s in sources], ignore_index=True)
    return df.astype({
        "date": "datetime64[ns]",
        "atc": pd.CategoricalDtype(settings.atc_groups),
        "source": pd.CategoricalDtype(sources),
        "granularity": pd.CategoricalDtype(sources),
    })
