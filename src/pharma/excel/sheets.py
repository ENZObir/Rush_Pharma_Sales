"""Une fonction par feuille, signature (writer, données) -> None. En-têtes en français, côté client."""

import pandas as pd
from openpyxl.utils import get_column_letter

from pharma.excel.writer import TemplateWriter
from pharma.features.calendar import add_calendar

QTY, INT, PCT, IDX, DEC = "#,##0.0", "#,##0", "0.0%", "0.00", "0.000"

MONTHS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août",
          "Septembre", "Octobre", "Novembre", "Décembre"]
WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
PAIRS_FR = {"hourly": "horaire", "daily": "journalier", "weekly": "hebdomadaire", "monthly": "mensuel"}


def _fr(x: float, decimals: int = 0) -> str:
    return f"{x:,.{decimals}f}".replace(",", " ").replace(".", ",")


def _pair_fr(pair: str) -> str:
    finer, coarser = pair.split("→")
    return f"{PAIRS_FR.get(finer, finer)} → {PAIRS_FR.get(coarser, coarser)}"


def write_sales(writer: TemplateWriter, clean_df: pd.DataFrame, atc_groups: list[str]) -> None:
    """Feuille Data : ventes journalières, une colonne par ATC, + colonnes calendrier et `Sélection` (formule).

    `Sélection` additionne les ATC cochés « Oui » dans la feuille Outil (ligne 9, mêmes colonnes que les ATC).
    """
    daily = clean_df[clean_df["source"] == "daily"]
    wide = (daily.pivot_table(index="date", columns="atc", values="quantity", aggfunc="sum", observed=True)
            .reindex(columns=atc_groups).reset_index())
    cal = add_calendar(wide[["date"]])

    first, last = get_column_letter(2), get_column_letter(1 + len(atc_groups))
    flags = f"Outil!$C$9:${get_column_letter(2 + len(atc_groups))}$9"
    out = pd.DataFrame({"Date": wide["date"]})
    for atc in atc_groups:
        out[atc] = wide[atc]
    out["Année"] = cal["year"]
    out["Mois"] = cal["month"]
    out["Jour (1 = lundi)"] = cal["weekday"] + 1
    out["Sélection"] = [f'=SUMPRODUCT({first}{r}:{last}{r}*({flags}="Oui"))' for r in range(2, len(out) + 2)]
    writer.write_table("tbl_ventes", out, {**{a: QTY for a in atc_groups}, "Sélection": QTY})


def write_data_quality(writer: TemplateWriter, report: pd.DataFrame, reconciliation: pd.DataFrame) -> None:
    rec = pd.DataFrame({
        "Comparaison": reconciliation["pair"].map(_pair_fr),
        "Cellules comparées": reconciliation["cells"],
        "Cellules en écart": reconciliation["gaps"],
        "Périodes en écart": reconciliation["periods_with_gap"],
        "Pire écart relatif": reconciliation["max_rel_gap"],
        "Période du pire écart": pd.to_datetime(reconciliation["worst_period"]),
        "ATC du pire écart": reconciliation["worst_atc"],
    })
    writer.write_table("tbl_reconciliation", rec, {"Cellules comparées": INT, "Cellules en écart": INT,
                                                   "Périodes en écart": INT, "Pire écart relatif": PCT})
    writer.write_table("tbl_qualite", report.rename(columns={
        "source": "Source", "type": "Type", "detail": "Constat", "decision": "Décision", "reason": "Raison"}))


def write_descriptive(writer: TemplateWriter, volumes: pd.DataFrame, variability: pd.DataFrame,
                      trend: pd.DataFrame) -> None:
    vol = volumes.merge(variability, on="atc", how="left")
    writer.write_table("tbl_volumes", pd.DataFrame({
        "ATC": vol["atc"], "Total (mois complets)": vol["total"], "Part du total": vol["share"],
        "Moyenne mensuelle": vol["monthly_mean"], "Mois": vol["months"],
        "Coefficient de variation": vol["cv"], "Stock de sécurité (1 mois)": vol["safety_stock"],
    }), {"Total (mois complets)": QTY, "Part du total": PCT, "Moyenne mensuelle": QTY, "Mois": INT,
         "Coefficient de variation": PCT, "Stock de sécurité (1 mois)": QTY})
    writer.write_table("tbl_tendance", pd.DataFrame({
        "ATC": trend["atc"], "Année": trend["year"], "Mois couverts": trend["months"], "Total": trend["total"],
        "Moyenne mensuelle": trend["monthly_mean"], "Évolution (mêmes mois)": trend["growth_same_months"],
    }), {"Total": QTY, "Moyenne mensuelle": QTY, "Évolution (mêmes mois)": PCT})


def write_seasonality(writer: TemplateWriter, profile: pd.DataFrame, atc_groups: list[str]) -> None:
    """Indices saisonniers (1 = moyenne) : mois × ATC, jour × ATC, heure × ATC."""
    specs = [("month", "tbl_saison_mois", "Mois", range(1, 13), lambda k: MONTHS[k - 1]),
             ("weekday", "tbl_saison_jour", "Jour", range(7), lambda k: WEEKDAYS[k]),
             ("hour", "tbl_saison_heure", "Heure", range(24), lambda k: f"{k:02d} h")]
    for dimension, table, label, keys, fmt in specs:
        p = profile[profile["dimension"] == dimension].assign(key=lambda d: d["key"].astype(int))
        wide = p.pivot_table(index="key", columns="atc", values="index", observed=True)
        wide = wide.reindex(index=list(keys), columns=atc_groups)
        out = pd.DataFrame({label: [fmt(k) for k in wide.index]})
        for atc in atc_groups:
            out[atc] = wide[atc].to_numpy()
        writer.write_table(table, out, {a: IDX for a in atc_groups})


def write_forecast(writer: TemplateWriter, forecast_next: pd.DataFrame, backtest: pd.DataFrame,
                   effect: pd.DataFrame) -> None:
    writer.write_table("tbl_prevision", pd.DataFrame({
        "ATC": forecast_next["atc"], "Mois prévu": forecast_next["month"].astype(str),
        "Prévision": forecast_next["yhat"], "Modèle retenu": forecast_next["model"],
        "Prévisible": forecast_next["verdict"],
    }), {"Prévision": QTY})
    writer.write_table("tbl_backtest", pd.DataFrame({
        "ATC": backtest["atc"], "Modèle": backtest["model"], "MAE": backtest["mae"], "MAPE": backtest["mape"],
        "MASE": backtest["mase"], "Gain vs meilleure baseline": backtest["gain_vs_baseline"],
    }), {"MAE": QTY, "MAPE": PCT, "MASE": DEC, "Gain vs meilleure baseline": PCT})
    writer.write_table("tbl_effet_externe", pd.DataFrame({
        "ATC": effect["atc"], "Variable": effect["variable"],
        "Corrélation (hors saisonnalité)": effect["corr"], "Δ MASE avec la variable": effect["delta_mase"],
    }), {"Corrélation (hors saisonnalité)": IDX, "Δ MASE avec la variable": DEC})


def summary_rows(data: dict[str, pd.DataFrame], last_complete: pd.Period) -> pd.DataFrame:
    """Chiffres clés, tous calculés depuis les sorties du pipeline."""
    clean, volumes = data["clean"], data["volumes"]
    fc, rec, effect = data["forecast_next"], data["reconciliation_summary"], data["external_effect"]
    daily = clean[clean["source"] == "daily"]
    top = volumes.iloc[0]
    yes, no = fc.loc[fc["verdict"] == "oui", "atc"].tolist(), fc.loc[fc["verdict"] != "oui", "atc"].tolist()

    rows = [
        ("Période couverte", f"{daily['date'].min():%d/%m/%Y} → {daily['date'].max():%d/%m/%Y}",
         "exports de caisse, 8 groupes ATC"),
        ("Dernier mois complet", last_complete.strftime("%m/%Y"), "les mois incomplets sont exclus des stats mensuelles"),
        ("Mois prévu", (last_complete + 1).strftime("%m/%Y"), "prévision par groupe dans la feuille Prévisions"),
        ("Groupe le plus vendu", f"{top['atc']} — {top['share']:.1%}".replace(".", ","),
         "part des quantités sur les mois complets"),
        ("Groupes prévisibles", f"{len(yes)} / {len(fc)}", ", ".join(yes) or "aucun"),
        ("Groupes non prévisibles", f"{len(no)} / {len(fc)}",
         (", ".join(no) + " : le modèle ne bat pas la prévision naïve") if no else "aucun"),
    ]
    for r in rec.itertuples(index=False):
        if r.gaps:
            rows.append((f"Export {_pair_fr(r.pair).split(' → ')[1]} fourni",
                         f"{_fr(r.gaps)} cellules en écart sur {_fr(r.cells)}",
                         f"écarté et recalculé ; pire écart {r.max_rel_gap:+.0%} ({r.worst_atc}, "
                         f"{pd.Timestamp(r.worst_period):%m/%Y})"))
    if not effect.empty:
        best = effect.loc[effect["corr"].abs().idxmax()]
        helped = effect.loc[effect["delta_mase"] < 0, "atc"].tolist()
        rows.append((f"Effet de la variable externe ({best['variable']})",
                     f"corrélation max {best['corr']:+.2f} ({best['atc']})".replace(".", ","),
                     f"améliore la MASE pour : {', '.join(helped)}" if helped
                     else "n'améliore la prévision d'aucun groupe"))
    return pd.DataFrame(rows, columns=["Indicateur", "Valeur", "Commentaire"])


def write_summary(writer: TemplateWriter, data: dict[str, pd.DataFrame], last_complete: pd.Period) -> None:
    writer.write_table("tbl_synthese", summary_rows(data, last_complete))
