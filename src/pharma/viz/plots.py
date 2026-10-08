"""Figures pour les decks et le mémo, enregistrées dans output/figures/ (PNG).

Une fonction par figure, chaque figure fermée après écriture. Jamais de double
axe : deux grandeurs d'échelles différentes vont dans deux panneaux. Les trois
couleurs de séries sont les trois premiers créneaux de la palette de référence,
validés pour la vision des couleurs déficiente.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # rendu fichier sans écran : marche aussi depuis un terminal distant ou en CI

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from pharma.forecast.backtest import BASELINES  # noqa: E402
from pharma.forecast.stage import ForecastStage, candidate_models  # noqa: E402

UNIT = "quantités enregistrées par le logiciel"
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
DIVERGING = LinearSegmentedColormap.from_list("sous_sur", ["#2a78d6", "#f0efec", "#e34948"])
SEQUENTIAL = LinearSegmentedColormap.from_list(
    "part", [SURFACE, "#cde2fb", "#86b6ef", "#2a78d6", "#184f95", "#0d366b"])

MODEL_LABELS = {"naive": "Naïf (M-1)", "seasonal_naive": "Naïf saisonnier (M-12)", "ets": "ETS",
                "sarima": "SARIMA", "sarimax": "SARIMA + grippe"}
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
WEEKDAYS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
RC = {"font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
      "font.size": 9.5, "text.color": INK, "axes.labelcolor": INK_2, "axes.edgecolor": AXIS,
      "xtick.color": INK_2, "ytick.color": INK_2, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
      "savefig.facecolor": SURFACE}


def _fr(value: float, decimals: int = 2, signed: bool = False) -> str:
    """Nombre au format français : virgule décimale (0,56 ; +0,04)."""
    return f"{value:{'+' if signed else ''}.{decimals}f}".replace(".", ",")


def _ink_on(rgba) -> str:
    """Blanc ou encre selon le contraste WCAG le plus élevé sur la couleur de la case."""
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgba[:3])
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "white" if 1.05 / (luminance + 0.05) > (luminance + 0.05) / 0.0534 else INK


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.savefig(path, dpi=200, bbox_inches="tight")
    finally:
        plt.close(fig)
    return path


def _titles(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=INK, pad=26 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.03, subtitle, transform=ax.transAxes, fontsize=9, color=INK_2, va="bottom")


def _lines_style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " ")))


def _heatmap(ax, table: pd.DataFrame, cmap, norm, labels: list[str], annotate):
    """Cases séparées par un liseré couleur de fond ; `annotate(ligne, colonne, valeur)` décide du texte affiché."""
    image = ax.imshow(table.to_numpy(), cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(table.shape[1]), labels)
    ax.set_yticks(range(table.shape[0]), table.index)
    ax.set_xticks(np.arange(-0.5, table.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, table.shape[0]), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for (i, j), value in np.ndenumerate(table.to_numpy()):
        text = annotate(i, j, value)
        if text:
            ax.text(j, i, text, ha="center", va="center", fontsize=8, color=_ink_on(cmap(norm(value))))
    return image


def _colorbar(fig, image, ax, label: str, decimals: int) -> None:
    bar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    bar.outline.set_visible(False)
    bar.ax.tick_params(length=0, labelsize=8, colors=INK_2)
    bar.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _fr(v, decimals)))
    bar.set_label(label, color=INK_2, fontsize=8.5)


def _gain_phrase(gain: float, baseline: str) -> str:
    direction = "de moins" if gain >= 0 else "de plus"
    name = MODEL_LABELS[baseline]
    return f"{_fr(abs(gain) * 100, 1)} % d'erreur {direction} que le {name[0].lower()}{name[1:]}"


def plot_backtest(stage: ForecastStage, atc: str, out_dir: Path) -> Path:
    """Backtest d'un ATC : réel vs meilleur modèle vs meilleure baseline, les deux courbes que le verdict compare."""
    results = stage.backtest_results[stage.backtest_results["atc"] == atc].set_index("model")
    models = [m for m in candidate_models() if m not in BASELINES]
    best = results.loc[models, "mae"].idxmin()
    baseline = results.loc[list(BASELINES), "mae"].idxmin()
    verdict = stage.forecast_next.set_index("atc").loc[atc, "verdict"]
    preds = stage.predictions[stage.predictions["atc"] == atc]
    curve = {name: preds[preds["model"] == name].set_index("target") for name in (best, baseline)}
    x = curve[best].index.to_timestamp()

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(9, 4.2))
        series = [("Réel", curve[best]["y_true"]), (MODEL_LABELS[best], curve[best]["y_pred"]),
                  (MODEL_LABELS[baseline], curve[baseline]["y_pred"])]
        for (label, values), color in zip(series, SERIES):
            ax.plot(x, values.to_numpy(), color=color, linewidth=2, solid_capstyle="round", label=label,
                    marker="o", markersize=4.5, markeredgecolor=SURFACE, markeredgewidth=1.2)
        _lines_style(ax)
        ax.set_ylabel(f"Ventes mensuelles ({UNIT})")
        ax.legend(loc="upper left", bbox_to_anchor=(0, -0.1), ncol=3, frameon=False)
        gain = results.loc[best, "gain_vs_baseline"]
        _titles(ax, f"{atc} — prévisible à un mois : « {verdict} »",
                f"{MODEL_LABELS[best]} : MASE {_fr(results.loc[best, 'mase'])}, {_gain_phrase(gain, baseline)} "
                f"sur {len(x)} mois prévus un par un (de {curve[best].index[0]} à {curve[best].index[-1]})")
        return _save(fig, out_dir / f"backtest_{atc}.png")


def plot_seasonality(profile: pd.DataFrame, out_dir: Path) -> Path:
    """Heatmap ATC × mois de l'indice saisonnier (1 = mois moyen de l'année)."""
    table = profile[profile["dimension"] == "month"].pivot(index="atc", columns="key", values="index").sort_index(axis=1)
    span = float(np.abs(table.to_numpy() - 1).max())
    norm = TwoSlopeNorm(vcenter=1, vmin=1 - span, vmax=1 + span)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(10, 4.4))
        image = _heatmap(ax, table, DIVERGING, norm, [MONTHS[int(k) - 1] for k in table.columns],
                         lambda i, j, v: _fr(v) if abs(v - 1) >= 0.3 else "")
        _colorbar(fig, image, ax, "Indice (1 = mois moyen)", 1)
        _titles(ax, "Saisonnalité mensuelle par groupe ATC",
                "Rouge : mois plus fort que la moyenne de l'année ; bleu : plus faible. "
                "Valeurs affichées si l'écart dépasse 30 %.")
        return _save(fig, out_dir / "saisonnalite_mois.png")


def plot_profiles(profile: pd.DataFrame, out_dir: Path) -> Path:
    """Deux heatmaps : indice par jour de la semaine, part des ventes par heure (heures actives seulement)."""
    week = profile[profile["dimension"] == "weekday"].pivot(index="atc", columns="key", values="index").sort_index(axis=1)
    hours = profile[profile["dimension"] == "hour"].pivot(index="atc", columns="key", values="index").sort_index(axis=1)
    hours = hours.loc[:, (hours > 0).any()] * 100
    span = float(np.abs(week.to_numpy() - 1).max())
    peak = hours.to_numpy().argmax(axis=1)

    with plt.rc_context(RC):
        fig, (left, right) = plt.subplots(1, 2, figsize=(15, 4.4), gridspec_kw={"width_ratios": [7, hours.shape[1]]})
        image = _heatmap(left, week, DIVERGING, TwoSlopeNorm(vcenter=1, vmin=1 - span, vmax=1 + span),
                         [WEEKDAYS[int(k)] for k in week.columns],
                         lambda i, j, v: _fr(v) if abs(v - 1) >= 0.2 else "")
        _colorbar(fig, image, left, "Indice (1 = jour moyen)", 1)
        _titles(left, "Jour de la semaine", "Valeurs affichées si l'écart dépasse 20 %.")
        image = _heatmap(right, hours, SEQUENTIAL, Normalize(vmin=0, vmax=float(hours.to_numpy().max())),
                         [f"{int(k)}h" for k in hours.columns],
                         lambda i, j, v: f"{v:.0f} %" if j == peak[i] else "")
        _colorbar(fig, image, right, "Part des ventes de la journée (%)", 0)
        _titles(right, "Heure de la journée", "Part de chaque heure dans les ventes du groupe ; pic de chaque groupe affiché.")
        return _save(fig, out_dir / "profils_jour_heure.png")


def plot_external(stage: ForecastStage, atc: str, out_dir: Path) -> Path:
    """Ventes d'un ATC et incidence grippale, en deux panneaux superposés (pas de double axe)."""
    effect = stage.external_effect.set_index("atc").loc[atc]
    flu = (stage.external[stage.external["variable"] == effect["variable"]]
           .set_index("month")["value"].reindex(stage.monthly.index))
    x = stage.monthly.index.to_timestamp()
    helps = "améliore" if effect["delta_mase"] < 0 else "n'améliore pas"

    with plt.rc_context(RC):
        fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 5.8), sharex=True, gridspec_kw={"hspace": 0.45})
        for ax, values, color, title in [
            (top, stage.monthly[atc], SERIES[0], f"Ventes mensuelles {atc} ({UNIT})"),
            (bottom, flu, SERIES[1], "Syndromes grippaux, France : incidence hebdomadaire moyenne pour 100 000 hab."),
        ]:
            ax.plot(x, values.to_numpy(), color=color, linewidth=2, solid_capstyle="round")
            ax.fill_between(x, values.to_numpy(), color=color, alpha=0.1, linewidth=0)
            ax.set_ylim(bottom=0)
            _lines_style(ax)
            ax.set_title(title, loc="left", fontsize=9.5, color=INK_2)
        fig.subplots_adjust(top=0.82)
        fig.suptitle(f"{atc} et grippe (Réseau Sentinelles)", x=0.125, y=0.985, ha="left", fontsize=12,
                     fontweight="bold", color=INK)
        fig.text(0.125, 0.925, f"Corrélation des écarts à l'an passé : {_fr(effect['corr'], signed=True)}. "
                 f"Ajouter la grippe du mois précédent {helps} la prévision "
                 f"(ΔMASE {_fr(effect['delta_mase'], 3, signed=True)}).", fontsize=9, color=INK_2)
        return _save(fig, out_dir / f"grippe_{atc}.png")


def save_figures(stage: ForecastStage, out_dir: Path, external_atc: list[str] | None = None) -> list[Path]:
    """Toutes les figures. ATC illustrés choisis par les données, jamais écrits en dur :
    « oui » = plus fort gain, « non » = plus gros volume ; `external_atc` vient de settings.yaml."""
    paths = [plot_seasonality(stage.seasonal_profile, out_dir), plot_profiles(stage.seasonal_profile, out_dir)]
    chosen = stage.forecast_next.merge(stage.backtest_results, on=["atc", "model"])
    oui, non = chosen[chosen["verdict"] == "oui"], chosen[chosen["verdict"] == "non"]
    if not oui.empty:
        paths.append(plot_backtest(stage, oui.loc[oui["gain_vs_baseline"].idxmax(), "atc"], out_dir))
    if not non.empty:
        paths.append(plot_backtest(stage, stage.monthly[non["atc"]].sum().idxmax(), out_dir))
    if not stage.external_effect.empty:
        paths += [plot_external(stage, atc, out_dir) for atc in external_atc or []]
    return paths
