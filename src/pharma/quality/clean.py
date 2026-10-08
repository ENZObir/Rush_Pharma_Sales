"""Applique les décisions qualité et produit le jeu de référence. Chaque décision est tracée dans le report.

Fonction pure : ni lecture ni écriture, `run_quality` sauvegarde le résultat.
Les constats sont calculés depuis les données : un mois de plus met le report à jour sans toucher au code.
"""

import pandas as pd

from pharma.config import Settings
from pharma.quality import checks
from pharma.quality.report import DataQualityReport

CLEAN_COLUMNS = ["date", "hour", "atc", "quantity", "source", "granularity", "complete_month"]


def _fr(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ")


def _pct(x: float) -> str:
    return f"{x:+.0%}".replace("%", " %")


def _report_reconciliation(reconciliation: pd.DataFrame, references: list[str],
                           report: DataQualityReport) -> None:
    for pair, r in reconciliation.groupby("pair", sort=False):
        finer, coarser = pair.split("→")
        bad = r[~r["ok"]]
        if bad.empty:
            detail = f"{finer} réagrégé = {coarser} fourni : 0 écart sur {_fr(len(r))} cellules"
            if coarser in references:
                decision, reason = f"{coarser} conservé", "cohérent avec la source plus fine"
            else:
                decision, reason = (f"{coarser} non utilisé (contrôle seulement)",
                                    f"redondant : recalculable à l'identique depuis {finer}")
        else:
            worst = bad.loc[bad["rel_gap"].abs().idxmax()]
            detail = (f"{_fr(len(bad))} cellules en écart sur {_fr(len(r))} "
                      f"({bad['period'].nunique()} périodes) ; pire : {worst['atc']} "
                      f"{worst['period']:%m/%Y}, {_fr(worst['actual'])} fourni vs "
                      f"{_fr(worst['expected'])} recalculé ({_pct(worst['rel_gap'])})")
            decision = (f"{coarser} écarté, recalculé depuis {finer}" if coarser not in references
                        else f"{coarser} conservé malgré les écarts — à vérifier")
            reason = f"incohérent avec {finer}, lui-même cohérent avec les autres exports"
        report.add(coarser, "réconciliation", detail, decision, reason)


def _drop_duplicates(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    dup = checks.duplicates(df)
    extra = len(dup) - len(dup.drop_duplicates(checks.KEY))
    if extra:
        report.add("toutes", "doublons", f"{_fr(extra)} lignes en double (date × heure × ATC × source)",
                   "première occurrence conservée", "une vente ne doit être comptée qu'une fois")
        df = df.drop_duplicates(checks.KEY)
    else:
        report.add("toutes", "doublons", "0 doublon", "rien à corriger", "contrôle effectué")
    return df


def _drop_negatives(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    neg = checks.negatives(df)
    if len(neg):
        report.add("toutes", "valeurs négatives", f"{_fr(len(neg))} quantités négatives",
                   "lignes retirées", "une quantité vendue ne peut pas être négative (retour ou erreur de saisie)")
        df = df.drop(neg.index)
    else:
        report.add("toutes", "valeurs négatives", "0 quantité négative", "rien à corriger", "contrôle effectué")
    return df


def _report_missing(df: pd.DataFrame, report: DataQualityReport) -> None:
    missing = checks.missing_days(df)
    for source, g in df.groupby("source", observed=True):
        m = missing[missing["source"] == source]
        span = f"du {g['date'].min():%d/%m/%Y} au {g['date'].max():%d/%m/%Y}"
        if m.empty:
            report.add(source, "périodes manquantes", f"0 période manquante {span}",
                       "rien à corriger", "contrôle effectué")
        else:
            report.add(source, "périodes manquantes", f"{_fr(len(m))} périodes absentes {span}",
                       "non comblées", "aucune valeur inventée ; à interpréter comme une absence de donnée")


def _report_non_integers(df: pd.DataFrame, report: DataQualityReport) -> None:
    for source, g in df.groupby("source", observed=True):
        ni = checks.non_integers(g)
        if ni.empty:
            continue
        by_atc = ni["atc"].value_counts()
        top = ", ".join(f"{atc} {_fr(n)}" for atc, n in by_atc[by_atc > 0].head(3).items())
        report.add(source, "quantités non entières",
                   f"{_fr(len(ni))} lignes sur {_fr(len(g))} (dont {top})",
                   "conservées, non arrondies",
                   "unité non documentée : probablement des fractions de boîte, rien ne permet de les corriger")


def _flag_complete_months(df: pd.DataFrame, settings: Settings,
                          report: DataQualityReport) -> pd.DataFrame:
    min_ratio = settings.quality["incomplete_month_ratio"]
    coverage = checks.month_coverage(df)
    complete = set(coverage.loc[coverage["ratio"] >= min_ratio, "month"])

    for row in coverage[coverage["ratio"] < 1].itertuples(index=False):
        detail = f"{row.month} : {row.days_present}/{row.days_in_month} jours"
        if row.ratio >= min_ratio:
            report.add("daily", "couverture", detail, "mois conservé",
                       f"couverture {row.ratio:.0%} ≥ seuil {min_ratio:.0%}")
        else:
            report.add("daily", "couverture", detail,
                       "exclu des stats mensuelles et de la prévision, conservé pour les profils jour/heure",
                       f"couverture {row.ratio:.0%} < seuil {min_ratio:.0%} : un total mensuel serait trompeur")

    df = df.copy()
    df["complete_month"] = df["date"].dt.to_period("M").isin(complete)
    return df


def _report_static(references: list[str], report: DataQualityReport) -> None:
    report.add("hourly, daily", "colonnes", "Year, Month, Hour, Weekday Name supprimées à l'import "
               "(Hour du journalier = somme des heures de la journée, sans sens métier)",
               "recalculées depuis la date", "une seule source de vérité pour le calendrier")
    report.add("toutes", "unité", "unité des quantités non documentée",
               "on parle de « quantités enregistrées par le logiciel »", "ne pas inventer une unité")
    if {"hourly", "daily"} <= set(references):
        report.add("hourly, daily", "source de référence",
                   "horaire → profils par heure ; journalier → tout le reste (jour, semaine, mois, prévision)",
                   "semaine et mois recalculés depuis le journalier",
                   "grain le plus fin utile à chaque usage, cohérence vérifiée par la réconciliation")


def clean(long_df: pd.DataFrame, settings: Settings, reconciliation: pd.DataFrame,
          report: DataQualityReport) -> pd.DataFrame:
    """Jeu de référence : sources de `quality.reference_sources`, anomalies traitées, `complete_month` ajouté."""
    references = settings.quality["reference_sources"]
    _report_reconciliation(reconciliation, references, report)

    df = long_df[long_df["source"].isin(references)]
    df = _drop_duplicates(df, report)
    df = _drop_negatives(df, report)
    _report_missing(df, report)
    _report_non_integers(df, report)
    df = _flag_complete_months(df, settings, report)
    _report_static(references, report)
    return df[CLEAN_COLUMNS].reset_index(drop=True)
