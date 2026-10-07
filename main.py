"""Point d'entrée unique : python main.py [--stage ...] [--no-external]."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pharma.config import load_settings  # noqa: E402

STAGES = ["quality", "stats", "forecast", "excel"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline Rush 2 Pharma")
    parser.add_argument("--stage", choices=STAGES + ["all"], default="all")
    parser.add_argument("--no-external", action="store_true",
                        help="ignore le réseau, utilise uniquement le cache")
    return parser.parse_args()


def run_quality(settings):
    raise NotImplementedError  # A : loaders → schema → reconciliation → checks → report


def run_stats(settings):
    raise NotImplementedError  # A : descriptive · B : seasonality, variability


def run_forecast(settings, use_external: bool):
    raise NotImplementedError  # B : external → baselines/models → backtest


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
