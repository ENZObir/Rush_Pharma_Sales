import pandas as pd
import pytest

from pharma.forecast.backtest import BASELINES
from pharma.forecast.stage import choose_models
from pharma.quality.checks import last_complete_month

CONTRACT = {
    "seasonal_profile": ["atc", "dimension", "key", "index"],
    "variability": ["atc", "cv", "safety_stock"],
    "backtest_results": ["atc", "model", "mae", "mape", "mase", "gain_vs_baseline"],
    "forecast_next": ["atc", "month", "yhat", "model", "verdict"],
    "external_effect": ["atc", "variable", "corr", "delta_mase"],
}


@pytest.fixture
def stage(real_stage):
    return real_stage


def test_outputs_have_exact_contract_columns(stage):
    outputs = stage.outputs()
    assert set(outputs) == set(CONTRACT)
    for name, columns in CONTRACT.items():
        assert list(outputs[name].columns) == columns, name


def test_one_row_per_atc(stage, real_settings):
    for name in ("variability", "forecast_next", "external_effect"):
        assert sorted(stage.outputs()[name]["atc"]) == sorted(real_settings.atc_groups), name
    assert set(stage.seasonal_profile["dimension"]) == {"month", "weekday", "hour"}


def test_incomplete_month_is_never_used(stage, real_long, real_settings):
    last = last_complete_month(real_long, real_settings.quality["incomplete_month_ratio"])
    assert stage.monthly.index.max() == last
    assert stage.predictions["target"].max() == last
    assert (stage.forecast_next["month"] == str(last + 1)).all()


def test_verdicts_are_consistent(stage):
    nxt = stage.forecast_next
    assert set(nxt["verdict"]) <= {"oui", "non"}
    assert nxt.loc[nxt["verdict"] == "non", "model"].isin(BASELINES).all()
    assert not nxt.loc[nxt["verdict"] == "oui", "model"].isin(BASELINES).any()
    assert nxt["yhat"].notna().all()


def results_frame(rows):
    return pd.DataFrame(rows, columns=["atc", "model", "mae", "gain_vs_baseline"])


def test_choose_models_by_hand():
    results = results_frame([
        ("N02BE", "naive", 10.0, 0.0), ("N02BE", "seasonal_naive", 12.0, -0.2), ("N02BE", "ets", 8.0, 0.2),
        ("R03", "naive", 10.0, 0.0), ("R03", "seasonal_naive", 11.0, -0.1), ("R03", "ets", 9.8, 0.02),
        ("N05C", "naive", 10.0, -0.25), ("N05C", "seasonal_naive", 8.0, 0.0), ("N05C", "ets", 9.0, -0.125),
        ("R06", "naive", 10.0, 0.0), ("R06", "seasonal_naive", 12.0, -0.2), ("R06", "sarimax", 1.0, 0.9),
    ])
    choice = choose_models(results, min_gain=0.05, candidates=["naive", "seasonal_naive", "ets", "sarima"])
    choice = choice.set_index("atc")
    assert choice.loc["N02BE"].tolist() == ["ets", "oui"]
    assert choice.loc["R03"].tolist() == ["naive", "non"]           # gain 2 % < 5 % : bruit
    assert choice.loc["N05C"].tolist() == ["seasonal_naive", "non"]  # une baseline gagne
    assert choice.loc["R06"].tolist() == ["naive", "non"]           # sarimax n'est pas candidat
