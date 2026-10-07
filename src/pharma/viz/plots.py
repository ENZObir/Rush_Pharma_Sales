"""Figures pour les decks et le mémo, enregistrées dans output/figures/."""

from pathlib import Path

import pandas as pd


def plot_seasonality(profile: pd.DataFrame, out_dir: Path) -> Path:
    raise NotImplementedError


def plot_backtest(backtest: pd.DataFrame, out_dir: Path) -> Path:
    raise NotImplementedError


def plot_external(monthly: pd.DataFrame, external: pd.DataFrame, out_dir: Path) -> Path:
    raise NotImplementedError
