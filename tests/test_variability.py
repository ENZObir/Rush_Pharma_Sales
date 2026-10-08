import math

import pandas as pd
import pytest

from pharma.stats.variability import VARIABILITY_COLUMNS, variability


def test_cv_and_safety_stock_by_hand():
    monthly = pd.DataFrame({"N02BE": [90.0, 100.0, 110.0], "R06": [10.0, 10.0, 10.0]},
                           index=pd.period_range("2019-07", periods=3, freq="M"))
    errors = pd.DataFrame({"atc": ["N02BE"] * 3 + ["R06"] * 3,
                           "error": [-4.0, 0.0, 4.0, 1.0, 1.0, 1.0]})
    out = variability(monthly, errors, z=1.65, lead_time_months=4)
    assert list(out.columns) == VARIABILITY_COLUMNS
    out = out.set_index("atc")
    assert out.loc["N02BE", "cv"] == pytest.approx(10 / 100)     # σ = 10 (échantillon), moyenne = 100
    assert out.loc["N02BE", "safety_stock"] == pytest.approx(1.65 * 4 * 2)  # σ erreurs = 4, √4 = 2
    assert out.loc["R06", "cv"] == 0
    assert out.loc["R06", "safety_stock"] == 0                   # erreur constante : biais, pas d'aléa


def test_atc_without_errors_gets_nan():
    monthly = pd.DataFrame({"N05C": [1.0, 2.0]}, index=pd.period_range("2019-08", periods=2, freq="M"))
    out = variability(monthly, pd.DataFrame({"atc": [], "error": []}), z=1.65, lead_time_months=1)
    assert math.isnan(out.loc[0, "safety_stock"])
