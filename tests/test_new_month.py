"""Le pipeline doit absorber un mois supplémentaire sans modification du code (aucune date en dur)."""

import dataclasses
import shutil

import pandas as pd
import pytest

from pharma.forecast.stage import compute_forecast_stage
from pharma.io.external import load_external
from pharma.io.loaders import load_all
from pharma.quality.checks import last_complete_month
from pharma.quality.clean import clean
from pharma.quality.reconciliation import reconcile_all
from pharma.quality.report import DataQualityReport
from pharma.stats.descriptive import monthly_sales


def _extend(path, fmt, start, end, freq):
    """Ajoute des lignes au CSV, en recopiant les quantités d'un mois plus tôt."""
    raw = pd.read_csv(path)
    stamps = pd.to_datetime(raw["datum"], format=fmt)
    by_stamp = raw.set_index(stamps)
    new = []
    for ts in pd.date_range(start, end, freq=freq):
        row = by_stamp.loc[ts - pd.DateOffset(months=1)].copy()
        row["datum"] = f"{ts.month}/{ts.day}/{ts.year}" + (f" {ts.hour}:00" if freq == "h" else "")
        row["Year"], row["Month"], row["Weekday Name"] = ts.year, ts.month, ts.day_name()
        row["Hour"] = ts.hour if freq == "h" else 276
        new.append(row)
    pd.concat([raw, pd.DataFrame(new)], ignore_index=True).to_csv(path, index=False)


@pytest.fixture(scope="module")
def extended_settings(real_settings, tmp_path_factory):
    raw_dir = tmp_path_factory.mktemp("raw")
    for f in real_settings.raw_files.values():
        shutil.copy(real_settings.raw_dir / f, raw_dir / f)
    fmt, files = real_settings.date_formats, real_settings.raw_files
    _extend(raw_dir / files["hourly"], fmt["hourly"], "2019-10-08 20:00", "2019-10-31 23:00", "h")
    _extend(raw_dir / files["daily"], fmt["daily"], "2019-10-09", "2019-10-31", "D")
    return dataclasses.replace(real_settings, raw_dir=raw_dir,
                               forecast={**real_settings.forecast, "backtest_months": 3})


def test_pipeline_absorbs_one_more_month(extended_settings):
    s = extended_settings
    long_df = load_all(s)
    assert last_complete_month(long_df, s.quality["incomplete_month_ratio"]) == pd.Period("2019-10", "M")

    report = DataQualityReport()
    clean_df = clean(long_df, s, reconcile_all(long_df, s.quality["reconciliation_tolerance"]), report)
    assert clean_df.loc[clean_df["date"].dt.month.eq(10) & clean_df["date"].dt.year.eq(2019), "complete_month"].all()
    assert monthly_sales(clean_df)["date"].max() == pd.Timestamp("2019-10-31")

    stage = compute_forecast_stage(s, clean_df, load_external(s, use_network=False))
    assert set(stage.forecast_next["month"]) == {"2019-11"}
