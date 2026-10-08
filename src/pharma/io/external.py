"""Récupération et cache des données publiques (Sentinelles, pollens, jours fériés…).

Le cache commité dans data/external/ fait foi : le pipeline tourne hors-ligne et
reste reproductible. Le réseau ne sert qu'à créer un cache absent, ou à le
rafraîchir sur demande (`refresh=True`).

Sortie commune (format long) : month (Period M), variable, value.
"""

import warnings
from pathlib import Path

import pandas as pd
import requests

from pharma.config import Settings

EXTERNAL_COLUMNS = ["month", "variable", "value"]
DEFAULT_TIMEOUT = 30


def read_sentinelles(path: Path) -> pd.DataFrame:
    """Export CSV sentiweb.fr tel quel : saute la ligne de métadonnées `#`, `-` = manquant."""
    with open(path, encoding="latin-1") as f:
        skip = 1 if f.readline().startswith("#") else 0
    raw = pd.read_csv(path, skiprows=skip, na_values=["-"], encoding="latin-1")
    missing = {"week", "inc100"} - set(raw.columns)
    if missing:
        raise ValueError(f"{path.name} : colonnes Sentinelles absentes : {sorted(missing)}")
    return raw


def sentinelles_monthly(raw: pd.DataFrame) -> pd.DataFrame:
    """Incidence hebdomadaire des syndromes grippaux → moyenne mensuelle pour 100 000 habitants.

    Une semaine ISO (`YYYYWW`) est rattachée au mois de son jeudi, comme l'ISO 8601
    rattache une semaine à l'année de son jeudi. Moyenne et non somme : un mois
    compte 4 ou 5 jeudis, une somme gonflerait artificiellement les mois à 5 semaines.
    """
    week = raw["week"].astype(int).astype(str)
    thursday = pd.to_datetime(week.str[:4] + "-W" + week.str[4:] + "-4", format="%G-W%V-%u")
    out = (
        pd.DataFrame({"month": thursday.dt.to_period("M"), "value": raw["inc100"].astype("float64")})
        .dropna(subset=["value"])
        .groupby("month")["value"]
        .mean()
        .reset_index()
    )
    out["variable"] = "syndromes_grippaux"
    return out[EXTERNAL_COLUMNS]


# nom dans settings.yaml → (lecture du fichier brut, transformation pure vers le format long)
SOURCES = {
    "sentinelles": (read_sentinelles, sentinelles_monthly),
}


def _source(settings: Settings, name: str) -> dict:
    configured = settings.external.get("sources") or {}
    if name not in configured:
        raise KeyError(f"source externe {name!r} absente de settings.yaml (external.sources)")
    if name not in SOURCES:
        raise KeyError(f"source externe {name!r} sans parseur ; connues : {sorted(SOURCES)}")
    return configured[name]


def _parse(name: str, path: Path) -> pd.DataFrame:
    read, transform = SOURCES[name]
    return transform(read(path))


def fetch(settings: Settings, name: str, use_network: bool = True, refresh: bool = False) -> Path:
    """Garantit la présence du cache data/external/<file> et renvoie son chemin.

    - cache présent et pas de `refresh` → aucun accès réseau ;
    - `use_network=False` → jamais de réseau, erreur si le cache manque ;
    - échec réseau → le cache existant est conservé (avertissement), erreur s'il n'y en a pas ;
    - fichier téléchargé de structure inattendue → erreur, le cache n'est pas écrasé.
    """
    source = _source(settings, name)
    path = settings.external_dir / source["file"]
    if path.exists() and (not refresh or not use_network):
        return path
    if not use_network:
        raise FileNotFoundError(f"{name} : cache absent ({path}) et réseau désactivé")

    timeout = settings.external.get("timeout", DEFAULT_TIMEOUT)
    try:
        response = requests.get(source["url"], timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        if path.exists():
            warnings.warn(f"{name} : téléchargement impossible ({exc}) ; cache conservé : {path}")
            return path
        raise FileNotFoundError(f"{name} : ni réseau ({exc}) ni cache ({path})") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_bytes(response.content)
    try:
        _parse(name, partial)
    except (ValueError, KeyError, pd.errors.ParserError) as exc:
        partial.unlink()
        raise ValueError(f"{name} : structure inattendue de {source['url']} : {exc}") from exc
    partial.replace(path)
    return path


def load_external(settings: Settings, use_network: bool = True, refresh: bool = False) -> pd.DataFrame:
    """Toutes les sources de settings.yaml (external.sources), au format long month/variable/value."""
    frames = [_parse(name, fetch(settings, name, use_network, refresh))
              for name in settings.external.get("sources") or {}]
    if not frames:
        return pd.DataFrame({"month": pd.PeriodIndex([], freq="M"),
                             "variable": pd.Series(dtype="object"),
                             "value": pd.Series(dtype="float64")})
    return pd.concat(frames, ignore_index=True)
