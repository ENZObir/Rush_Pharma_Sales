import pandas as pd
import pytest

from pharma.stats.descriptive import monthly_sales, volumes_and_shares, yearly_trend


def monthly(rows):
    df = pd.DataFrame(rows, columns=["date", "atc", "quantity"])
    df["date"] = pd.to_datetime(df["date"])
    df["atc"] = df["atc"].astype("category")
    return df


def test_monthly_sales_excludes_incomplete_months(real_clean):
    df, _ = real_clean
    m = monthly_sales(df)
    assert m["date"].max() == pd.Timestamp("2019-09-30")
    assert m["date"].nunique() == 69


def test_shares_sum_to_one_and_sorted(real_clean):
    v = volumes_and_shares(monthly_sales(real_clean[0]))
    assert v["share"].sum() == pytest.approx(1)
    assert v["total"].is_monotonic_decreasing
    assert v.iloc[0]["atc"] == "N02BE"


def test_growth_compares_same_months_only():
    df = monthly([("2018-01-31", "A", 10), ("2018-02-28", "A", 10), ("2018-03-31", "A", 100),
                  ("2019-01-31", "A", 12), ("2019-02-28", "A", 13)])
    t = yearly_trend(df).set_index("year")
    assert t.loc[2019, "months"] == 2
    assert t.loc[2019, "growth_same_months"] == pytest.approx(25 / 20 - 1)   # mars 2018 ignoré
    assert pd.isna(t.loc[2018, "growth_same_months"])
