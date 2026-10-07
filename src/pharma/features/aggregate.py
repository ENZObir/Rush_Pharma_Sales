"""Une seule fonction d'agrégation, paramétrée par granularité."""

import pandas as pd

from pharma.io.loaders import LONG_COLUMNS

# Étiquettes alignées sur les exports : semaine lun → dim datée du dimanche, mois daté du dernier jour.
GRANULARITIES = {
    "D": ("D", "daily"),
    "W": ("W-SUN", "weekly"),
    "M": ("ME", "monthly"),
}


def aggregate(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    """Somme des quantités par source × atc × période. granularity ∈ {"D", "W", "M"}. Contrat A → B.

    Entrée et sortie au format long. `source` garde l'export d'origine (les sources
    ne sont jamais additionnées entre elles), `granularity` devient la granularité cible.
    """
    if granularity not in GRANULARITIES:
        raise ValueError(f"granularity doit être dans {list(GRANULARITIES)}, reçu {granularity!r}")
    freq, name = GRANULARITIES[granularity]

    out = (
        df.groupby(["source", "atc", pd.Grouper(key="date", freq=freq)], observed=True)["quantity"]
        .sum()
        .reset_index()
    )
    out["hour"] = pd.Series(pd.NA, index=out.index, dtype="Int8")
    out["granularity"] = pd.Categorical([name] * len(out), categories=df["granularity"].cat.categories)
    return out[LONG_COLUMNS]
