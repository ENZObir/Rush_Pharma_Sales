"""Réagrégation hourly → daily → weekly → monthly et comparaison aux fichiers fournis."""

import numpy as np
import pandas as pd

from pharma.features.aggregate import GRANULARITIES, aggregate

# Paires comparées : (source fine réagrégée, export fourni au grain plus grossier).
PAIRS = [("hourly", "daily"), ("daily", "weekly"), ("daily", "monthly")]

RECONCILIATION_COLUMNS = ["pair", "period", "atc", "expected", "actual", "abs_gap", "rel_gap", "ok"]

_CODE = {name: code for code, (_, name) in GRANULARITIES.items()}


def reconcile(long_df: pd.DataFrame, finer: str, coarser: str, tolerance: float) -> pd.DataFrame:
    """Écarts par atc × période entre `finer` réagrégé au grain de `coarser` et l'export `coarser`.

    expected = valeur recalculée depuis `finer` ; actual = valeur de l'export fourni.
    abs_gap = actual − expected ; rel_gap = abs_gap / expected ; ok = |rel_gap| ≤ tolerance.
    Une période absente d'un des deux côtés donne une valeur manquante et ok = False.
    """
    if coarser not in _CODE:
        raise ValueError(f"impossible de réagréger vers {coarser!r}")

    recomputed = aggregate(long_df[long_df["source"] == finer], _CODE[coarser])
    provided = long_df[long_df["source"] == coarser]

    key = ["date", "atc"]
    out = (
        recomputed.set_index(key)["quantity"].rename("expected").to_frame()
        .join(provided.set_index(key)["quantity"].rename("actual"), how="outer")
        .reset_index()
        .rename(columns={"date": "period"})
    )
    out["atc"] = out["atc"].astype(long_df["atc"].dtype)
    out["abs_gap"] = out["actual"] - out["expected"]
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = out["abs_gap"] / out["expected"]
    out["rel_gap"] = rel.where(out["expected"] != 0, np.where(out["abs_gap"] == 0, 0.0, np.inf))
    out["ok"] = out["rel_gap"].abs() <= tolerance
    out.insert(0, "pair", f"{finer}→{coarser}")
    return out[RECONCILIATION_COLUMNS]


def reconcile_all(long_df: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """Enchaîne toutes les comparaisons de PAIRS dans un seul tableau."""
    return pd.concat([reconcile(long_df, f, c, tolerance) for f, c in PAIRS], ignore_index=True)


def summarize(reconciliation: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par paire : cellules comparées, cellules en écart, pire écart relatif et sa position."""
    rows = []
    for pair, r in reconciliation.groupby("pair", sort=False):
        bad = r[~r["ok"]]
        worst = r.loc[r["rel_gap"].abs().idxmax()] if r["rel_gap"].notna().any() else None
        rows.append({
            "pair": pair,
            "cells": len(r),
            "gaps": len(bad),
            "periods_with_gap": bad["period"].nunique(),
            "max_rel_gap": None if worst is None else worst["rel_gap"],
            "worst_period": None if worst is None else worst["period"],
            "worst_atc": None if worst is None else worst["atc"],
        })
    return pd.DataFrame(rows)
