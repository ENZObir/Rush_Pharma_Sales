import pandas as pd

from pharma.quality.clean import CLEAN_COLUMNS, clean
from pharma.quality.report import DataQualityReport


def test_keeps_reference_sources_only(real_clean, real_settings):
    df, _ = real_clean
    assert list(df.columns) == CLEAN_COLUMNS
    assert set(df["source"]) == set(real_settings.quality["reference_sources"])


def test_incomplete_month_flagged_not_removed(real_clean):
    df, _ = real_clean
    by_month = df.groupby(df["date"].dt.to_period("M"))["complete_month"].first()
    assert not by_month[pd.Period("2019-10", "M")]
    assert by_month[pd.Period("2019-09", "M")]
    assert by_month[pd.Period("2014-01", "M")]          # 30/31 jours, au-dessus du seuil
    assert (df["date"] >= "2019-10-01").any()           # octobre gardé pour les profils jour/heure


def test_every_decision_is_reported(real_clean):
    _, report = real_clean
    findings = report.to_frame()
    assert {"réconciliation", "doublons", "valeurs négatives", "périodes manquantes",
            "quantités non entières", "couverture", "colonnes", "unité",
            "source de référence"} <= set(findings["type"])
    monthly = findings[(findings["source"] == "monthly") & (findings["type"] == "réconciliation")].iloc[0]
    assert "écarté" in monthly["decision"] and "45" in monthly["detail"]


def test_duplicates_and_negatives_are_removed(real_long, real_settings, real_reconciliation):
    daily = real_long[real_long["source"] == "daily"]
    dirty = pd.concat([real_long, daily.iloc[[3]]], ignore_index=True)
    dirty.loc[dirty.index[10], "quantity"] = -2.0
    report = DataQualityReport()
    out = clean(dirty, real_settings, real_reconciliation, report)
    types = report.to_frame().set_index("type")["detail"]
    assert types["doublons"].startswith("1 ")
    assert types["valeurs négatives"].startswith("1 ")
    assert (out["quantity"] >= 0).all()
    assert not out.duplicated(["date", "hour", "atc", "source"]).any()


def test_raw_input_untouched(real_long, real_settings, real_reconciliation):
    before = real_long.copy()
    clean(real_long, real_settings, real_reconciliation, DataQualityReport())
    pd.testing.assert_frame_equal(real_long, before)
