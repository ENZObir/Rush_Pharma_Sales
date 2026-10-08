import pandas as pd
import pytest

from pharma.quality.reconciliation import RECONCILIATION_COLUMNS, reconcile, summarize


def test_columns(real_reconciliation):
    assert list(real_reconciliation.columns) == RECONCILIATION_COLUMNS


def test_hourly_daily_weekly_are_consistent(real_reconciliation):
    s = summarize(real_reconciliation).set_index("pair")
    assert s.loc["hourly→daily", "gaps"] == 0
    assert s.loc["daily→weekly", "gaps"] == 0


def test_monthly_export_is_inconsistent(real_reconciliation):
    s = summarize(real_reconciliation).set_index("pair").loc["daily→monthly"]
    assert s["gaps"] == 45
    assert s["worst_atc"] == "N02BE"
    assert s["worst_period"] == pd.Timestamp("2014-10-31")
    assert s["max_rel_gap"] == pytest.approx(0.749, abs=1e-3)


def test_period_missing_on_one_side_is_flagged(real_long):
    drop = (real_long["source"] == "weekly") & (real_long["date"] == "2016-05-08") & (real_long["atc"] == "R06")
    out = reconcile(real_long[~drop], "daily", "weekly", tolerance=0.01)
    row = out[(out["period"] == "2016-05-08") & (out["atc"] == "R06")].iloc[0]
    assert pd.isna(row["actual"]) and not row["ok"]


def test_cannot_reconcile_to_hourly(real_long):
    with pytest.raises(ValueError):
        reconcile(real_long, "daily", "hourly", tolerance=0.01)
