import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pharma.config import load_settings  # noqa: E402
from pharma.io.loaders import load_all  # noqa: E402


@pytest.fixture(scope="session")
def real_settings():
    return load_settings()


@pytest.fixture(scope="session")
def real_long(real_settings):
    """Les 4 exports réels au format long (contrat A → B), chargés une fois par session."""
    return load_all(real_settings)
