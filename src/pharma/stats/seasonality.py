"""Profils mensuel / jour / heure et indices saisonniers.

Une source par dimension (format long, une seule `source`, période déjà limitée
aux mois complets par l'appelant) :
- month   : mensuel (journalier agrégé) — indice, 1 = mois moyen de l'année ;
- weekday : journalier — indice, 1 = jour moyen ;
- hour    : horaire, seule source avec `hour` — PART du total (somme = 1), pas un indice.
"""

import pandas as pd

PROFILE_COLUMNS = ["atc", "dimension", "key", "index"]


def _month_index(df: pd.DataFrame) -> pd.DataFrame:
    """Ratio au niveau moyen de l'année, moyenné par mois : la tendance pluriannuelle est neutralisée.

    Seules les années aux 12 mois présents comptent : une année partielle biaiserait sa propre moyenne.
    """
    d = df.assign(year=df["date"].dt.year, key=df["date"].dt.month)
    n_months = d.groupby(["atc", "year"], observed=True)["key"].transform("nunique")
    d = d[n_months == 12]
    if d.empty:
        raise ValueError("aucune année complète (12 mois) pour le profil mensuel")
    ratio = d["quantity"] / d.groupby(["atc", "year"], observed=True)["quantity"].transform("mean")
    out = ratio.groupby([d["atc"], d["key"]], observed=True).mean().rename("index").reset_index()
    out["key"] = out["key"].map("{:02d}".format)
    return out


def _weekday_index(df: pd.DataFrame) -> pd.DataFrame:
    """Moyenne du jour de la semaine / moyenne journalière globale de l'ATC. key 0 = lundi."""
    d = df.assign(key=df["date"].dt.dayofweek)
    by_day = d.groupby(["atc", "key"], observed=True)["quantity"].mean()
    overall = d.groupby("atc", observed=True)["quantity"].mean()
    out = by_day.div(overall, level="atc").rename("index").reset_index()
    out["key"] = out["key"].astype(str)
    return out


def _hour_share(df: pd.DataFrame) -> pd.DataFrame:
    """Part de chaque heure dans le total de l'ATC, sur les journées complètes (24 heures) seulement."""
    hours_per_day = df.groupby("date")["hour"].transform("nunique")
    d = df[hours_per_day == 24]
    by_hour = d.groupby(["atc", "hour"], observed=True)["quantity"].sum()
    out = by_hour.div(by_hour.groupby(level="atc", observed=True).transform("sum")).rename("index").reset_index()
    out["key"] = out["hour"].astype(int).map("{:02d}".format)
    return out


PROFILES = {"month": _month_index, "weekday": _weekday_index, "hour": _hour_share}


def seasonal_profile(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """dimension ∈ {"month", "weekday", "hour"}. Sortie : PROFILE_COLUMNS. Contrat B → A."""
    if dimension not in PROFILES:
        raise ValueError(f"dimension doit être dans {list(PROFILES)}, reçu {dimension!r}")
    sources = df["source"].astype(str).unique()
    if len(sources) != 1:
        raise ValueError(f"une seule source attendue, reçu {sorted(sources)}")
    if dimension == "hour" and df["hour"].isna().all():
        raise ValueError("profil horaire : `hour` vide, seule la source horaire convient")
    out = PROFILES[dimension](df).assign(dimension=dimension)
    out["atc"] = out["atc"].astype(str)
    return out[PROFILE_COLUMNS].reset_index(drop=True)
