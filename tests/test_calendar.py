import pandas as pd

from pharma.features.calendar import add_calendar


def test_dimensions_derived_from_date():
    df = pd.DataFrame({"date": pd.to_datetime(["2014-01-02", "2016-02-29", "2019-12-30"])})
    out = add_calendar(df)
    assert out["year"].tolist() == [2014, 2016, 2019]
    assert out["month"].tolist() == [1, 2, 12]
    assert out["weekday"].tolist() == [3, 0, 0]          # jeudi, lundi, lundi
    assert out["iso_week"].tolist() == [1, 9, 1]          # le 30/12/2019 est en semaine ISO 1 de 2020
    assert out["month_period"].astype(str).tolist() == ["2014-01", "2016-02", "2019-12"]


def test_input_not_modified():
    df = pd.DataFrame({"date": pd.to_datetime(["2014-01-02"])})
    add_calendar(df)
    assert list(df.columns) == ["date"]
