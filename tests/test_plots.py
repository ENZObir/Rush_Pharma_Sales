import warnings

import matplotlib.pyplot as plt

from pharma.viz.plots import _fr, save_figures


def test_save_figures_writes_pngs_and_closes_everything(real_stage, real_settings, tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # glyphe manquant, police introuvable… : échec plutôt que figure abîmée
        paths = save_figures(real_stage, tmp_path, real_settings.external["figure_atc"])
    names = {p.name for p in paths}
    assert {"saisonnalite_mois.png", "profils_jour_heure.png"} <= names
    assert {f"grippe_{atc}.png" for atc in real_settings.external["figure_atc"]} <= names
    assert sum(name.startswith("backtest_") for name in names) == real_stage.forecast_next["verdict"].nunique()
    for path in paths:
        assert path.parent == tmp_path and path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert plt.get_fignums() == []


def test_french_number_format():
    assert _fr(0.5612) == "0,56"
    assert _fr(0.04, signed=True) == "+0,04"
    assert _fr(-0.0081, 3, signed=True) == "-0,008"
