# Fiches de poste — A et B (plan réduit, 2 jours restants)

*Complément de `ARCHITECTURE.MD` §7. Chaque tâche a une **définition de « fini »**. Le périmètre a été réduit pour tenir en J2 + J3 à deux : ce qui est marqué **bonus** ne se fait que si tout le reste est fini.*

**Règle n°1 : gel du code J2 au soir.** J3 est entièrement consacré au mémo, aux decks et aux oraux. Ce qui n'est pas fini J2 au soir est coupé, pas reporté.

---

## Ce qui est acquis

| Module | État |
|---|---|
| Arborescence, `config.py`, `settings.yaml`, `requirements.txt`, `.gitignore`, CLI `main.py` | ✅ |
| `io/loaders.py` + `quality/schema.py` : 4 CSV → format long (424 080 lignes) | ✅ |
| `features/aggregate.py` : `aggregate(df, "D"/"W"/"M")`, étiquettes alignées sur les exports | ✅ |
| `quality/checks.py` : trous, doublons, négatifs, non-entiers, `month_coverage`, `last_complete_month` | ✅ |
| `quality/report.py` : `DataQualityReport` | ✅ (aucun finding encore enregistré) |

**Faits établis sur les données** (à ne pas redécouvrir, à réutiliser dans les decks) :

- Horaire = journalier = hebdomadaire une fois réagrégés (écarts < 1e-7) → les 3 sont cohérents.
- **`Monthly.csv` est incohérent** avec le journalier : 45 cellules sur 560, pire cas octobre 2014 (N02BE 1 830 fourni vs 1 046 recalculé, +75 %). → **écarté, mensuel recalculé depuis le journalier.**
- Aucun jour manquant, aucun doublon, aucune valeur négative.
- 17 887 quantités non entières (dont 5 548 au journalier) → signalées, **pas corrigées** (unité non documentée).
- `last_complete_month` = **2019-09** → mois à prévoir : **octobre 2019**. Octobre 2019 = 8 jours, exclu des stats mensuelles et de la prévision, **conservé** pour les profils jour/heure.
- Janvier 2014 = 30/31 jours (1ᵉʳ janvier férié) → considéré complet.
- `Hour` du journalier = somme des heures de la journée (276 = 0+…+23) → preuve que le journalier est dérivé de l'horaire.

---

## A — Données → Classeur

> **Livre à B :** `load_all`, `aggregate`, `last_complete_month` (✅ disponibles), puis le jeu propre de `clean`.
> **Reçoit de B :** les DataFrames de résultats (§7.2), qu'il écrit dans le classeur.

### J2 matin — finir la qualité

| Fichier | À faire | Fini quand |
|---|---|---|
| `quality/reconciliation.py` *(en cours)* | Comparer hourly→D, daily→W, daily→M aux fichiers fournis. Sortie : `period, atc, pair, expected, actual, abs_gap, rel_gap`. | Le tableau retrouve les 45 écarts du mensuel et 0 ailleurs. |
| `quality/clean.py` *(nouveau)* | `clean(long_df, settings, report)` : garde `hourly` + `daily` seulement, ajoute `complete_month` (bool), enregistre chaque décision dans le report. Sauvegarde dans `data/processed/`. | B, les stats et Excel ne lisent plus que ce jeu-là. |
| `main.run_quality` | Enchaîne `load_all` → `reconcile_all` → `checks` → `clean`, et ajoute **un finding par décision** : mensuel écarté, hebdo = contrôle seulement, horaire pour les profils intra-jour, journalier pour le reste, octobre 2019 exclu du mensuel, colonnes dérivées supprimées, unité non documentée, quantités décimales conservées, 1ᵉʳ janvier 2014 absent. | `python main.py --stage quality` tourne et écrit le report. |

### J2 après-midi — stats et classeur

| Fichier | À faire | Fini quand |
|---|---|---|
| `features/calendar.py` | `add_calendar` : `year`, `month`, `weekday` (0 = lundi). Le reste seulement si un module en a besoin. | Dérivé de `date` uniquement. |
| `stats/descriptive.py` | Volume total et part par ATC, évolution annuelle sur **années complètes** (2014 → 2018, 2019 sur 9 mois à comparer à 9 mois). | 3 chiffres utilisables tels quels dans un deck. |
| `templates/outil_pharma.xlsx` *(à la main dans Excel)* | Feuilles **Synthèse**, **Statistiques**, **État des données**, **Prévisions**, **Outil**, **Data**. Chaque feuille data = un **tableau nommé**. Outil : 2 listes déroulantes (ATC, mois) + `FILTER` / `SUMIFS`. **Pas de TCD ni de segments.** | Un non-pythoniste choisit un ATC et une période et voit les ventes ; aucune macro, aucune `#REF!`. |
| `excel/writer.py` | Copie le template vers `output/`, réécrit le contenu d'un tableau nommé et **redimensionne sa plage** (`table.ref`). | Le fichier généré s'ouvre sans alerte de réparation. |
| `excel/sheets.py` | Une fonction par feuille : `write_data_quality`, `write_sales_long` (journalier propre), `write_descriptive`, `write_seasonality`, `write_forecast`, `write_summary`. | Toutes les stats du classeur viennent du code. |
| `main.run_stats`, `main.run_excel` | Lisent/écrivent `data/processed/`. | `python main.py` régénère le classeur. |

**→ J2 soir : premier `python main.py` de bout en bout avec B, puis gel du code.**

**Bonus A** : `test_reconciliation.py`, `test_calendar.py`, test « mois supplémentaire ».

---

## B — Prévision & environnement

> **Reçoit de A :** `load_all`, `aggregate`, `last_complete_month` (✅ disponibles).
> **Série mensuelle à utiliser :** `aggregate(df[df.source == "daily"], "M")`, filtrée sur `date <= last_complete_month`. **Jamais `source == "monthly"`** (incohérent).
> **Cible :** octobre 2019. **Fenêtre de backtest :** 24 derniers mois complets (oct. 2017 → sept. 2019).

### J2 matin — le protocole de prévision (le cœur de la note)

| Fichier | À faire | Fini quand |
|---|---|---|
| `forecast/metrics.py` | `mae`, `mape` (exclure les mois à 0 ou passer en sMAPE, et le dire), `mase` (échelle = MAE du naïf saisonnier sur le train, `period=12`), `gain_vs_baseline = 1 − err_modèle / err_baseline`. | Vérifié à la main sur 3 valeurs. |
| `forecast/baselines.py` | `Naive` (M = M-1), `SeasonalNaive` (M = M-12), interface `Forecaster`. | `predict` renvoie une Series indexée par les mois futurs. |
| `forecast/backtest.py` | `rolling_origin` : pour chaque mois test M, entraîner sur les mois < M seulement, prévoir M, modèle **recréé** à chaque origine. `run_backtests` : boucle ATC × modèles → `backtest_results`. | Aucune donnée ≥ M dans le train. |
| `tests/test_backtest.py` | **Obligatoire.** Faux modèle qui enregistre `y.index.max()` à chaque `fit` ; vérifier `< date prévue` pour toutes les origines. | `pytest` vert. |

### J2 après-midi — modèle, saisonnalité, donnée externe

| Fichier | À faire | Fini quand |
|---|---|---|
| `forecast/models.py` → `ETS` | `ExponentialSmoothing` de statsmodels, saisonnalité additive 12, tendance amortie. Si échec de convergence : fallback sur `SeasonalNaive` + log. | Le backtest tourne sur les 8 ATC. |
| `forecast_next` | Par ATC : meilleur modèle au backtest, prévision d'octobre 2019, `verdict` = `oui` si MASE < 1 **et** meilleur que les deux baselines, sinon `non`. | Une réponse par groupe, assumée même si c'est « non ». |
| `stats/seasonality.py` | `seasonal_profile` : `month` sur le mensuel recalculé (années complètes), `weekday` sur le journalier, `hour` sur l'horaire. Format `atc, dimension, key, index`. | On retrouve R06 au printemps, R03/N02BE en hiver. |
| `io/external.py` | **Une seule source.** Recommandé : **Réseau Sentinelles** (incidence hebdo des syndromes grippaux) pour N02BE/R03. Plan B si le téléchargement bloque : jours fériés + vacances scolaires (data.gouv.fr). Télécharger une fois, commiter le cache dans `data/external/`, noter l'URL et la date. | Le pipeline tourne avec `--no-external`. |
| `external_effect` | Par ATC concerné : corrélation ventes ↔ variable **en écart à la saisonnalité** (pas sur les séries brutes). | Au moins une phrase de recommandation pour le deck Propriétaire. |
| `stats/variability.py` | `cv` = écart-type / moyenne mensuelle ; `safety_stock` = 1,65 × écart-type mensuel. | Un chiffre par ATC. |

**→ J2 soir : premier `python main.py` de bout en bout avec A, puis gel du code.**

**Bonus B** (seulement si tout ce qui précède est fini) : `SARIMA` à ordre fixe `(1,0,0)(0,1,1,12)` ; `ExogRegression` avec la variable externe décalée d'un mois et `delta_mase` ; stock de sécurité basé sur l'erreur de prévision.

### J3 matin — figures

`viz/plots.py`, **3 figures seulement** : heatmap saisonnalité ATC × mois, MASE par ATC (ligne à 1), N02BE vs incidence grippale. PNG dans `output/figures/`.

---

## Planning

| | A | B | Ensemble |
|---|---|---|---|
| **J2 matin** | `reconciliation`, `clean`, `run_quality` | `metrics`, `baselines`, `backtest`, `test_backtest` | **9h** : point sur l'avancée de B |
| **J2 après-midi** | `calendar`, `descriptive`, template Excel, `writer`, `sheets` | `ETS`, `forecast_next`, `seasonality`, `external`, `variability` | **14h** : B confirme la source externe |
| **J2 soir** | | | **`python main.py` complet → gel du code** |
| **J3 matin** | Mémo partie 2, deck Propriétaire, test clone vierge, README | Mémo partie 1, deck Manager, figures | |
| **J3 après-midi** | | | Deck Pharmacien, puis **répétition des 3 oraux** (chacun en présente au moins un) |

## Hors code

| | A | B |
|---|---|---|
| **Mémo PDF** | Partie 2 : risques du partage (réidentification horaire N05B/N05C, RGPD art. 9, CSP R.4235-5, L.1453-3), recommandation tranchée | Partie 1 : prévision (protocole, résultats, verdict par groupe) |
| **Decks** (5 slides max) | Propriétaire : effets internes/externes, recommandations, offre du labo | Manager : méthode, mensuel incohérent détecté, backtest, mission de suivi |
| **Ensemble** | Pharmacien : A fait la démo de l'outil, B la saisonnalité et les groupes prévisibles | |

## Points de vigilance communs

- Ne jamais écrire `2019`, `09` ou un nom d'ATC en dur : tout vient de `settings.yaml` ou des données.
- Petits commits fréquents, une branche par module, PR relue par l'autre.
- Si un contrat (§3 ou §7.2) doit changer : on en parle d'abord, puis on met `ARCHITECTURE.MD` à jour.
