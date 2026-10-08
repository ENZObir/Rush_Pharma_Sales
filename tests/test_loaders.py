from pharma.io.loaders import LONG_COLUMNS

EXPECTED_ROWS = {"hourly": 50_532, "daily": 2_106, "weekly": 302, "monthly": 70}


def test_long_format_contract(real_long, real_settings):
    assert list(real_long.columns) == LONG_COLUMNS
    assert str(real_long["date"].dtype) == "datetime64[ns]"
    assert str(real_long["hour"].dtype) == "Int8"
    assert real_long["quantity"].dtype == "float64"
    assert list(real_long["atc"].cat.categories) == real_settings.atc_groups
    assert not real_long["quantity"].isna().any()


def test_one_row_per_csv_line_and_atc(real_long, real_settings):
    counts = real_long.groupby("source", observed=True).size().to_dict()
    n_atc = len(real_settings.atc_groups)
    assert counts == {s: n * n_atc for s, n in EXPECTED_ROWS.items()}


def test_dates_parsed_month_first(real_long):
    first = real_long.loc[real_long["source"] == "daily", "date"].min()
    assert (first.year, first.month, first.day) == (2014, 1, 2)
    assert first.day_name() == "Thursday"  # cohérent avec « Weekday Name » du CSV


def test_hour_only_for_hourly(real_long):
    hourly = real_long["source"] == "hourly"
    assert real_long.loc[hourly, "hour"].between(0, 23).all()
    assert real_long.loc[~hourly, "hour"].isna().all()
    assert (real_long["date"] == real_long["date"].dt.normalize()).all()
