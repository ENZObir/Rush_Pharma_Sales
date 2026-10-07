# Fiches de poste — A et B

*Complément de `ARCHITECTURE.MD` §7. Chaque tâche a une **définition de « fini »** : tant qu'elle n'est pas vraie, la tâche n'est pas finie.*

**Faits vérifiés sur les données** (à ne pas redécouvrir) :

| Fichier | Lignes | Format date | Particularité |
|---|---|---|---|
| Hourly | 50 532 | `1/2/2014 8:00` | colonnes `Year/Month/Hour/Weekday Name` à ignorer |
| Daily | 2 106 | `1/2/2014` | `Hour = 248` absurde ; aucun jour manquant entre le 02/01/2014 et le 08/10/2019 |
| Weekly | 302 | `1/5/2014` | daté au **dimanche de fin de semaine** (lundi → dimanche), 1ʳᵉ semaine partielle |
| Monthly | 70 | `2014-01-31` | ISO fin de mois ; la ligne `2019-10-31` ne couvre que 8 jours |

---

## A — Données → Classeur

> **Question portée :** « Les données sont-elles fiables, et le client peut-il s'en servir sans nous ? »
> **Livre à B :** le format long, `aggregate`, `last_complete_month`.
> **Reçoit de B :** les 5 DataFrames de résultats (§7.2), qu'il écrit dans le classeur.

### A1. Socle — J1 matin (priorité absolue : B en dépend)

| Fichier | À faire | Fini quand |
|---|---|---|
| `config.py` | Déjà fonctionnel. Ajouter un champ si `settings.yaml` grossit. | `load_settings()` marche depuis n'importe quel dossier. |
| `io/loaders.py` | **Stub d'abord** : `load_all` qui ne lit que `Monthly.csv` et renvoie le format long. Le pousser sur `main` avant midi. Puis la vraie version : lire les 4 CSV, `melt` des 8 colonnes ATC → `atc`/`quantity`, ajouter `source`, `granularity`, `hour` (Int8, rempli seulement pour hourly). | Sortie = exactement les 6 colonnes et dtypes de §3 ; `atc` ∈ les 8 groupes de `settings.yaml`. |
| `quality/schema.py` | `parse_dates` avec le format **explicite** de `settings.yaml` (jamais d'inférence). `normalize` : drop `Year/Month/Hour/Weekday Name`, dates à minuit sauf hourly, `quantity` en float64. | Aucune `NaT` ; le 1/2/2014 est bien un jeudi 2 janvier. |

### A2. Qualité des données — J1 après-midi

| Fichier | À faire | Fini quand |
|---|---|---|
| `features/aggregate.py` | `aggregate(df, "D"/"W"/"M")` : somme par `atc` × période. `W` = `W-SUN` (étiquette au dimanche, comme Weekly.csv), `M` = mois. Une seule fonction. | Daily → W reproduit la 1ʳᵉ ligne de Weekly (N02BE = 185,95). |
| `quality/reconciliation.py` | Comparer hourly→daily, daily→weekly, daily→monthly, et weekly→monthly si utile. Sortie : `period, atc, pair, expected, actual, abs_gap, rel_gap`. Un écart > tolérance = un finding. | Tableau des écarts complet ; chaque écart notable a une explication (arrondi, semaine partielle, mois incomplet…). |
| `quality/checks.py` | `missing_days` (calendrier continu vs dates présentes), `duplicates` (date×hour×atc×source), `negatives`, `non_integers` (les quantités décimales existent : M01AE = 3,67 → les compter, pas les corriger), `last_complete_month` (part de jours couverts ≥ seuil). | `last_complete_month` renvoie **2019-09** sans qu'aucune date soit écrite dans le code. |
| `quality/report.py` | Déjà fonctionnel. Dans `main.run_quality`, ajouter **un finding par décision** : source retenue par usage (hourly → profils intra-jour, daily → le reste), exclusion d'octobre 2019, colonnes droppées, unité non documentée (« quantités enregistrées par le logiciel »), quantités non entières. | La feuille « État des données » se lit seule : source, constat, décision, raison. |
| `tests/test_reconciliation.py`, `tests/test_calendar.py` | Remplacer les `skip` par de vrais tests. | `pytest` vert. |

**→ J1 18h : annoncer à B le dernier mois complet et les écarts de réconciliation qui le concernent.**

### A3. Features et statistiques descriptives — J2 matin

| Fichier | À faire | Fini quand |
|---|---|---|
| `features/calendar.py` | `add_calendar` : `year`, `month`, `iso_week`, `weekday` (0 = lundi), `month_period`. Tout dérivé de `date`. | Aucune colonne calendaire ne vient d'un CSV. |
| `stats/descriptive.py` | `volumes_and_shares` : volume total et part par ATC (par année et global). `yearly_trend` : évolution annuelle, **années complètes seulement** ou ramenées au même nombre de mois. Exclure le mois incomplet. | Chaque chiffre soutient une phrase du deck (« N02BE = X % des volumes »). |

### A4. Classeur et outil — J2 après-midi

| Élément | À faire | Fini quand |
|---|---|---|
| `templates/outil_pharma.xlsx` *(fait dans Excel, pas en Python)* | Feuilles : **Synthèse**, **Statistiques**, **Saisonnalité**, **Prévisions**, **État des données**, **Outil**, **Data** (cachée ou en dernier). Chaque feuille data = un **tableau nommé** (`tbl_ventes`, `tbl_qualite`…). Feuille **Outil** : listes déroulantes (validation des données) pour ATC et période, formules `FILTER` / `SUMIFS` / `LET` pointant sur les tableaux nommés — ou TCD + segments + chronologie. | Un utilisateur sans Python sélectionne plusieurs ATC et une période et voit les ventes ; aucune macro, aucune `#REF!`. |
| `excel/writer.py` | `TemplateWriter` : copie le template vers `output/`, vide et réécrit le contenu d'un tableau nommé, **redimensionne sa plage** (`table.ref`), ne touche à aucune autre feuille. | Ouvrir le fichier généré dans Excel : aucune alerte de réparation. |
| `excel/sheets.py` | Une fonction par feuille. `write_sales_long` écrit le format long journalier + horaire (c'est la source de l'outil). `write_summary` reprend 3 à 5 chiffres clés depuis les autres DataFrames. | Toutes les stats du classeur viennent du code. |
| `main.py` | Implémenter `run_quality` / `run_stats` / `run_excel` : chaque étape lit et écrit ses intermédiaires dans `data/processed/` (parquet ou CSV) pour pouvoir être relancée seule. | `python main.py --stage excel` marche seul si les étapes d'avant ont tourné. |

**→ J2 17h : premier `python main.py` de bout en bout avec B.**

### A5. Reproductibilité — J3 matin

- `git clone` dans un dossier temporaire → `python -m venv .venv` → `pip install -r requirements.txt` → `python main.py`. Corriger tout ce qui casse.
- **Test « mois supplémentaire »** : dupliquer un mois fictif dans une copie des CSV, relancer, vérifier que rien n'est à modifier dans le code.
- Ouvrir le classeur dans **Excel 365** et tester l'outil comme un client.
- README : installation, commande, structure, tableau « qui a fait quoi ».
- Vérifier le dépôt : pas de `.venv`, `__pycache__`, `output/`, brouillons.

---

## B — Prévision & environnement

> **Question portée :** « Peut-on prévoir le mois suivant, et quelle part des ventes vient de l'environnement ? »
> **Reçoit de A :** `load_all`, `aggregate`, `last_complete_month` (stub dès J1 midi).
> **Livre à A :** `seasonal_profile`, `variability`, `backtest_results`, `forecast_next`, `external_effect`.

### B1. Donnée externe et métriques — J1 matin (sans attendre A)

| Fichier | À faire | Fini quand |
|---|---|---|
| `io/external.py` | Choisir **une** source principale + une secondaire. Recommandé : **Réseau Sentinelles** (incidence hebdo des syndromes grippaux, CSV téléchargeable) pour N02BE / R03, et **jours fériés + vacances scolaires** (data.gouv.fr) pour les creux. Pollens (RNSA) pour R06 si accessible. `fetch` télécharge une fois, écrit `data/external/<nom>.csv`, puis lit le cache ; `use_network=False` ne touche jamais au réseau. | Le pipeline tourne hors-ligne avec le cache commité ; l'URL et la date de téléchargement sont notées en tête de fichier ou dans `settings.yaml`. |
| `forecast/metrics.py` | `mae`, `mape` (gérer les zéros : N05C a des mois très bas → l'exclure ou utiliser sMAPE, le dire), `mase` (échelle = MAE du naïf **saisonnier** sur le train, `period=12`), `gain_vs_baseline = 1 - err_modèle / err_baseline`. | Testé à la main sur 3 valeurs. |
| `forecast/baselines.py` | `Naive` (M = M-1) et `SeasonalNaive` (M = M-12). `predict` renvoie une Series indexée par les mois futurs. | Respectent l'interface `Forecaster`. |

### B2. Backtest — J1 après-midi

| Fichier | À faire | Fini quand |
|---|---|---|
| `forecast/backtest.py` | `rolling_origin` : pour chaque mois test M (les `backtest_months` derniers mois **complets**), entraîner sur `y[:M-1]`, prévoir M. Le modèle est **recréé** à chaque origine (`make_model()`). `run_backtests` boucle sur ATC × modèles et calcule les métriques. | Aucune donnée ≥ M dans l'entraînement ; octobre 2019 n'apparaît nulle part. |
| `tests/test_backtest.py` | Test anti-fuite : un faux modèle qui enregistre `y.index.max()` à chaque `fit` ; vérifier `< date prévue` pour toutes les origines. | `pytest` vert. |

**→ J1 18h : récupérer de A le dernier mois complet et figer cible + fenêtre de test.**

### B3. Modèles et saisonnalité — J2 matin

| Fichier | À faire | Fini quand |
|---|---|---|
| `forecast/models.py` | `ETS` : `statsmodels` `ExponentialSmoothing` (tendance additive amortie, saisonnalité 12 ; variante sans tendance). `SARIMA` : `SARIMAX` avec un ordre simple fixe, ex. `(1,0,0)(0,1,1,12)` — pas d'auto-ARIMA par ATC, trop long et sur-ajusté. Gérer les échecs de convergence (fallback sur la baseline + log). | Le backtest tourne sur les 8 ATC en moins de quelques minutes. |
| `stats/seasonality.py` | `seasonal_profile(df, "month")` sur le **mensuel** (moyenne du mois / moyenne annuelle, années complètes), `"weekday"` sur le **journalier**, `"hour"` sur l'**horaire**. Sortie au format long `atc, dimension, key, index` (1 = moyenne). | On retrouve R06 au printemps, R03 et N02BE en hiver — sinon, chercher pourquoi. |

### B4. Effet externe et variabilité — J2 après-midi

| Fichier | À faire | Fini quand |
|---|---|---|
| `forecast/models.py` → `ExogRegression` | Régression des ventes mensuelles sur la variable externe (+ saisonnalité via dummies de mois ou SARIMAX avec `exog`). **La valeur externe du mois prévu doit être connue à M-1** : utiliser la valeur décalée (lag 1) ou le dire explicitement. | Entre dans le même backtest que les autres. |
| Calcul de `external_effect` | Par ATC : corrélation ventes ↔ variable (sur données désaisonnalisées ou en écart à la normale, pas brutes) **et** `delta_mase` = MASE avec exogène − MASE sans. | Au moins une ligne permet une recommandation (« le pic grippal explique X % de… »). |
| `stats/variability.py` | `cv` = écart-type / moyenne mensuelle par ATC. `safety_stock` = `z × σ(erreur de prévision du meilleur modèle)` avec z = 1,65 (95 %) ; à défaut σ des ventes. | Chiffre par ATC, unité « quantités logiciel ». |
| `forecast_next` | Pour chaque ATC : meilleur modèle au backtest, prévision du mois suivant le dernier mois complet, `verdict` = `oui` si MASE < 1 **et** gain > 0 vs les deux baselines, sinon `non`. | Une réponse par groupe, assumée même si c'est « non ». |

**→ J2 17h : premier `python main.py` de bout en bout avec A.**

### B5. Figures — J3 matin

| Fichier | À faire |
|---|---|
| `viz/plots.py` | `plot_seasonality` (heatmap ATC × mois), `plot_backtest` (MASE par ATC et modèle, ligne à 1), `plot_external` (ventes N02BE vs incidence grippale). PNG dans `output/figures/`, mêmes couleurs par ATC partout. |

---

## Hors code — proposition

| | A | B |
|---|---|---|
| **Mémo PDF** | Partie 2 : risques du partage (réidentification horaire N05B/N05C, RGPD art. 9, CSP R.4235-5, L.1453-3, recommandation tranchée) | Partie 1 : réponse sur la prévision (protocole, résultats, verdict par groupe) |
| **Decks** | Propriétaire (effets internes, recommandations, offre du labo) | Manager (méthode, qualité, backtest, mission de suivi) |
| **Ensemble** | Deck Pharmacien acheteur : A fait la démo de l'outil, B la saisonnalité et la prévisibilité | |
| **J3 après-midi** | Chacun répète **les trois** oraux, chacun en présente au moins un | |

## Points de vigilance communs

- Ne jamais écrire `2019`, `09` ou un nom d'ATC en dur : tout vient de `settings.yaml` ou des données.
- Petits commits fréquents, une branche par module, PR relue par l'autre.
- Si un contrat (§3 ou §7.2) doit changer : on en parle d'abord, puis on met `ARCHITECTURE.MD` à jour.
