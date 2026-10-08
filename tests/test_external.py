import dataclasses

import pandas as pd
import pytest
import requests

from pharma.config import load_settings
from pharma.io import external
from pharma.io.external import EXTERNAL_COLUMNS, fetch, load_external, sentinelles_monthly

SENTINELLES_CSV = (
    '# {"meta": "en-tete de test"}\n'
    "week,indicator,inc,inc_low,inc_up,inc100,inc100_low,inc100_up,geo_insee,geo_name\n"
    "201902,3,1,1,1,30,1,1,FR,France\n"
    "201901,3,1,1,1,10,1,1,FR,France\n"
    "201852,3,-,,,-,,,FR,France\n"
).encode("latin-1")


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self) -> None:
        pass


def _offline(*args, **kwargs):
    raise requests.ConnectionError("hors-ligne")


def _forbidden(*args, **kwargs):
    raise AssertionError("aucun accès réseau attendu")


@pytest.fixture
def settings(tmp_path):
    return dataclasses.replace(load_settings(), external_dir=tmp_path)


@pytest.fixture
def cache(settings):
    return settings.external_dir / settings.external["sources"]["sentinelles"]["file"]


def test_week_assigned_to_month_of_its_thursday():
    raw = pd.DataFrame({"week": [201401, 201501, 201553, 201901], "inc100": [1.0, 2.0, 3.0, 4.0]})
    out = sentinelles_monthly(raw).set_index("month")["value"]
    # 2015-W01 commence le lundi 29/12/2014 mais son jeudi est le 01/01/2015
    assert out[pd.Period("2015-01", "M")] == 2.0
    assert out[pd.Period("2015-12", "M")] == 3.0  # semaine 53, jeudi 31/12/2015
    assert out[pd.Period("2014-01", "M")] == 1.0
    assert out[pd.Period("2019-01", "M")] == 4.0  # commence le lundi 31/12/2018


def test_monthly_value_is_mean_of_weeks_and_skips_missing(settings, cache):
    cache.write_bytes(SENTINELLES_CSV)
    out = load_external(settings, use_network=False)
    assert list(out.columns) == EXTERNAL_COLUMNS
    assert out["month"].tolist() == [pd.Period("2019-01", "M")]
    assert out["value"].tolist() == [20.0]  # (10 + 30) / 2, la semaine « - » est ignorée


def test_existing_cache_is_read_without_network(settings, cache, monkeypatch):
    cache.write_bytes(SENTINELLES_CSV)
    monkeypatch.setattr(external.requests, "get", _forbidden)
    assert fetch(settings, "sentinelles") == cache


def test_no_network_and_no_cache_raises(settings, monkeypatch):
    monkeypatch.setattr(external.requests, "get", _forbidden)
    with pytest.raises(FileNotFoundError, match="réseau désactivé"):
        fetch(settings, "sentinelles", use_network=False)


def test_missing_cache_is_downloaded(settings, cache, monkeypatch):
    monkeypatch.setattr(external.requests, "get", lambda url, timeout: FakeResponse(SENTINELLES_CSV))
    assert fetch(settings, "sentinelles") == cache
    assert cache.read_bytes() == SENTINELLES_CSV


def test_network_failure_falls_back_to_cache(settings, cache, monkeypatch):
    cache.write_bytes(SENTINELLES_CSV)
    monkeypatch.setattr(external.requests, "get", _offline)
    with pytest.warns(UserWarning, match="cache conservé"):
        assert fetch(settings, "sentinelles", refresh=True) == cache


def test_network_failure_without_cache_raises(settings, monkeypatch):
    monkeypatch.setattr(external.requests, "get", _offline)
    with pytest.raises(FileNotFoundError, match="ni réseau"):
        fetch(settings, "sentinelles")


def test_unexpected_structure_keeps_previous_cache(settings, cache, monkeypatch):
    cache.write_bytes(SENTINELLES_CSV)
    monkeypatch.setattr(external.requests, "get",
                        lambda url, timeout: FakeResponse(b"<html>maintenance</html>"))
    with pytest.raises(ValueError, match="structure inattendue"):
        fetch(settings, "sentinelles", refresh=True)
    assert cache.read_bytes() == SENTINELLES_CSV
    assert not list(settings.external_dir.glob("*.part"))
