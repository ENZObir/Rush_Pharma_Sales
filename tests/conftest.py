import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pharma.config import load_settings  # noqa: E402
from pharma.forecast.stage import compute_forecast_stage  # noqa: E402
from pharma.io.external import load_external  # noqa: E402
from pharma.io.loaders import load_all  # noqa: E402


@pytest.fixture(scope="session")
def real_settings():
    return load_settings()


@pytest.fixture(scope="session")
def real_long(real_settings):
    """Les 4 exports réels au format long (contrat A → B), chargés une fois par session."""
    return load_all(real_settings)


@pytest.fixture(scope="session")
def real_stage(real_settings, real_long):
    """Étape forecast sur les vraies données, fenêtre de test courte (3 mois) pour garder la suite rapide."""
    fast = dataclasses.replace(real_settings, forecast={**real_settings.forecast, "backtest_months": 3})
    return compute_forecast_stage(fast, real_long, load_external(fast, use_network=False))


@pytest.fixture(scope="session")
def real_reconciliation(real_settings, real_long):
    from pharma.quality.reconciliation import reconcile_all
    return reconcile_all(real_long, real_settings.quality["reconciliation_tolerance"])


@pytest.fixture(scope="session")
def real_clean(real_settings, real_long, real_reconciliation):
    """Jeu de référence produit par quality/clean.py, avec son DataQualityReport."""
    from pharma.quality.clean import clean
    from pharma.quality.report import DataQualityReport
    report = DataQualityReport()
    return clean(real_long, real_settings, real_reconciliation, report), report
