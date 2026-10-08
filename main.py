"""Point d'entrée unique : python main.py [--stage ...] [--no-external]."""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pharma.config import ROOT, load_settings  # noqa: E402
from pharma.forecast.stage import compute_forecast_stage  # noqa: E402
from pharma.io.external import load_external  # noqa: E402
from pharma.io.loaders import load_all  # noqa: E402
from pharma.quality.clean import clean  # noqa: E402
from pharma.quality.reconciliation import reconcile_all, summarize  # noqa: E402
from pharma.quality.report import DataQualityReport  # noqa: E402
from pharma.viz.plots import save_figures  # noqa: E402

STAGES = ["quality", "stats", "forecast", "excel"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline Rush 2 Pharma")
    parser.add_argument("--stage", choices=STAGES + ["all"], default="all")
    parser.add_argument("--no-external", action="store_true",
                        help="ignore le réseau, utilise uniquement le cache")
    return parser.parse_args()


def clean_path(settings):
    return settings.processed_dir / "quality" / "clean.pkl"


def load_clean(settings):
    """Jeu de référence produit par l'étape quality (lu par les étapes suivantes)."""
    path = clean_path(settings)
    if not path.exists():
        sys.exit(f"{path.relative_to(ROOT)} absent : lancer d'abord `python main.py --stage quality`")
    return pd.read_pickle(path)


def run_quality(settings):
    """A : 4 exports → réconciliation → nettoyage → data/processed/quality/ (jeu propre + état des données)."""
    long_df = load_all(settings)
    reconciliation = reconcile_all(long_df, settings.quality["reconciliation_tolerance"])
    report = DataQualityReport()
    clean_df = clean(long_df, settings, reconciliation, report)

    out_dir = clean_path(settings).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    clean_df.to_pickle(clean_path(settings))
    reconciliation.to_csv(out_dir / "reconciliation.csv", index=False)
    summarize(reconciliation).to_csv(out_dir / "reconciliation_summary.csv", index=False)
    report.to_frame().to_csv(out_dir / "data_quality_report.csv", index=False)

    gaps = (~reconciliation["ok"]).sum()
    print(f"  {len(clean_df):,} lignes de référence ({', '.join(settings.quality['reference_sources'])})")
    print(f"  réconciliation : {gaps} cellules en écart sur {len(reconciliation):,}")
    print(f"  {len(report.findings)} constats → {out_dir.relative_to(ROOT)}")


def run_stats(settings):
    raise NotImplementedError  # A : descriptive · B : seasonality, variability


def run_forecast(settings, use_external: bool):
    """B : backtest, prévision, saisonnalité, variabilité, effet externe → data/processed/forecast/ + figures."""
    external = load_external(settings, use_network=use_external)
    stage = compute_forecast_stage(settings, load_clean(settings), external)

    out_dir = settings.processed_dir / "forecast"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in stage.outputs().items():
        df.to_csv(out_dir / f"{name}.csv", index=False)

    figures = save_figures(stage, settings.figures_dir, settings.external.get("figure_atc"))
    print(f"  dernier mois complet : {stage.last_complete_month}")
    print(f"  {len(stage.outputs())} tables → {out_dir.relative_to(ROOT)}")
    print(f"  {len(figures)} figures → {settings.figures_dir.relative_to(ROOT)}")


def run_excel(settings):
    raise NotImplementedError  # A : writer + sheets


def main() -> None:
    args = parse_args()
    settings = load_settings()
    settings.processed_dir.mkdir(parents=True, exist_ok=True)

    stages = STAGES if args.stage == "all" else [args.stage]
    for stage in stages:
        print(f"[{stage}]")
        if stage == "quality":
            run_quality(settings)
        elif stage == "stats":
            run_stats(settings)
        elif stage == "forecast":
            run_forecast(settings, use_external=not args.no_external)
        elif stage == "excel":
            run_excel(settings)


if __name__ == "__main__":
    main()
