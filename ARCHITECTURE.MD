# Architecture du code — Rush 2 Pharma

*Document de référence pour l'équipe. À lire avant d'écrire la première ligne.*

---

## 1. Principes

| Principe | Conséquence concrète |
|---|---|
| **Un seul point d'entrée** | `python main.py` lit, contrôle, calcule, régénère le classeur. `main.py` orchestre, ne calcule rien. |
| **Un format canonique unique** | `io/loaders.py` est le seul module qui connaît la forme des CSV. Tout le reste ne voit que le format long. |
| **Aucune date, aucune dimension en dur** | Les groupes ATC viennent de `settings.yaml`, le dernier mois complet est *calculé* depuis les données. Ajouter un mois ne touche aucun fichier. |
| **Logique métier = fonctions pures** | `stats/` et `forecast/` font `DataFrame → DataFrame`. Zéro I/O, zéro `print`. Testable gratuitement. |
| **Chemins relatifs à la racine du repo** | `config.py` résout tout depuis `Path(__file__).parents[2]`. Fonctionne depuis un clone vierge. |
| **Le template Excel n'est jamais régénéré** | Python réécrit seulement les feuilles de données du modèle `.xlsx`. |

---

## 2. Arborescence

```
rush_2/
├── main.py                     # seul point d'entrée, orchestrateur + CLI
├── requirements.txt
├── README.md                   # qui a fait quoi
├── ARCHITECTURE.MD             # ce document
├── .gitignore
│
├── config/
│   └── settings.yaml           # chemins, groupes ATC, params backtest, seuils
│
├── data/
│   ├── raw/                    # les 4 exports fournis            [commité]
│   ├── external/               # cache des données publiques      [commité]
│   └── processed/              # intermédiaires générés           [gitignored]
│
├── templates/
│   └── outil_pharma.xlsx       # classeur-modèle contenant l'outil [commité]
│
├── output/                     #                                  [gitignored]
│   ├── Analyse_Pharma.xlsx
│   └── figures/
│
├── src/pharma/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── io/
│   │   ├── loaders.py          # 4 exports → format long canonique
│   │   └── external.py         # fetch + cache données publiques
│   │
│   ├── quality/
│   │   ├── schema.py           # normalisation colonnes, dtypes, parsing dates
│   │   ├── reconciliation.py   # hourly→daily→weekly→monthly + écarts
│   │   ├── checks.py           # trous, doublons, négatifs, non-entiers, mois incomplet
│   │   └── report.py           # DataQualityReport → feuille « État des données »
│   │
│   ├── features/
│   │   ├── calendar.py         # year/month/iso_week/weekday/hour DÉRIVÉS
│   │   └── aggregate.py        # agrégations ATC × granularité
│   │
│   ├── stats/
│   │   ├── descriptive.py      # volumes, parts, tendance pluriannuelle
│   │   ├── seasonality.py      # profils mensuel / jour / heure, indices saisonniers
│   │   └── variability.py      # CV, dimensionnement du stock de sécurité
│   │
│   ├── forecast/
│   │   ├── baselines.py        # naive, seasonal_naive
│   │   ├── models.py           # ETS, SARIMA, régression exogène
│   │   ├── backtest.py         # origine glissante
│   │   └── metrics.py          # MAE, MAPE, MASE
│   │
│   ├── excel/
│   │   ├── writer.py           # ouvre le template, remplace les feuilles data
│   │   └── sheets.py           # une fonction par feuille
│   │
│   └── viz/
│       └── plots.py            # figures pour les decks et le mémo
│
└── tests/
    ├── test_calendar.py
    ├── test_reconciliation.py
    └── test_backtest.py        # anti-fuite : max(train.date) < date prévue
```

---

## 3. Le contrat central : le format long

**Tout** ce qui circule entre les couches respecte ce schéma :

| Colonne | Type | Notes |
|---|---|---|
| `date` | `datetime64[ns]` | normalisée à minuit pour les granularités ≥ jour |
| `hour` | `Int8` (nullable) | renseigné uniquement depuis l'export horaire |
| `atc` | `category` | l'un des 8 groupes de `settings.yaml` |
| `quantity` | `float64` | « quantités enregistrées par le logiciel » — unité non documentée |
| `source` | `category` | `hourly` / `daily` / `weekly` / `monthly` |
| `granularity` | `category` | granularité native de la source |

`io/loaders.py` produit ce format et rien d'autre. C'est la seule interface à figer dès la première heure : ensuite les trois chantiers avancent en parallèle sans se bloquer.

---

## 4. Pièges vérifiés dans les données

À traiter dans `quality/schema.py`, pas ailleurs.

1. **Format de date `m/d/Y`.** `1/2/2014` + `Thursday` ⇒ 2 janvier 2014, qui était bien un jeudi. À passer explicitement à `pd.to_datetime(..., format=...)` : sans ça, pandas inférera d/m/Y sur une partie des lignes.
2. **`Monthly` a un format différent** : `2014-01-31` (ISO, fin de mois) et pas de colonnes dérivées. Un parseur par source, pas un parseur global.
3. **`Daily.csv` contient `Hour = 248`** — valeur sans signification, résidu d'agrégation. Toutes les colonnes `Year / Month / Hour / Weekday Name` sont **droppées à l'import** et recalculées par `features/calendar.py`.
4. **`Weekly` est daté au dimanche de fin de semaine** (`1/5/2014` = somme du jeudi 2 au dimanche 5, vérifié sur N02BE). Semaine lundi → dimanche, donc réagréger avec `W-SUN` ; la première semaine est partielle.
5. **Octobre 2019 incomplet** (8 jours, jusqu'au 8/10 ; la ligne `Monthly` est pourtant datée du 31). `checks.py` le détermine, ne le suppose pas, et l'exclut des stats mensuelles et de l'évaluation des prévisions.

---

## 5. Détail des couches

### `config.py`
`Settings` (dataclass, chargée depuis `settings.yaml`) : chemins absolus résolus depuis la racine du repo, liste des groupes ATC, horizon et longueur de fenêtre de backtest, seuils de contrôle qualité. **Aucun chemin local, aucune date.**

### `quality/`
- `reconciliation.py` : réagrège horaire → journalier → hebdomadaire → mensuel et compare aux fichiers fournis. Retourne un tableau d'écarts (absolu + relatif) par ATC × période.
- `checks.py` : jours manquants, doublons, valeurs négatives, quantités non entières, dernier mois incomplet.
- `report.py` : `DataQualityReport` accumule des findings typés — `source`, `type`, `détail`, `décision`, `raison`. La feuille « État des données » n'est qu'une sérialisation de cet objet : impossible que le log et le classeur divergent.

**Choix de source par usage** (documenté dans le rapport) : l'horaire pour les profils intra-journée, le journalier pour tout le reste.

### `features/`
`calendar.py` dérive toutes les dimensions temporelles de `date`. `aggregate.py` expose une seule fonction d'agrégation paramétrée par granularité — pas quatre fonctions quasi identiques.

### `forecast/`
Interface commune à tous les prédicteurs, baselines incluses :

```python
class Forecaster(Protocol):
    def fit(self, y: pd.Series, X: pd.DataFrame | None = None) -> "Forecaster": ...
    def predict(self, h: int, X: pd.DataFrame | None = None) -> pd.Series: ...
```

`backtest.py` ne connaît donc aucun modèle en particulier : ajouter SARIMA ne le modifie pas. Il n'implémente qu'une chose, l'origine glissante — on prévoit M avec les données jusqu'à M-1 seulement, sur 12 à 24 mois de test. **Aucune validation croisée aléatoire.** `test_backtest.py` verrouille cette propriété.

`metrics.py` fournit MASE et gain relatif vs baseline, pas seulement MAE/MAPE : c'est la métrique qui tranche la question « oui / non / seulement pour certains » par groupe.

### `excel/`
`writer.py` ouvre `templates/outil_pharma.xlsx` et réécrit **uniquement** les feuilles de données, exposées en **tables nommées** pour que les formules du template y pointent de façon stable. L'outil (validation de données + `FILTER`/`LET`, ou TCD + segments) vit dans le template et n'est jamais touché par le code — générer un TCD ou un segment avec openpyxl est fragile.

`sheets.py` : une fonction par feuille, signature `(writer, data) -> None`.

---

## 6. Exécution

```bash
pip install -r requirements.txt
python main.py                    # pipeline complet
python main.py --stage quality    # quality | stats | forecast | excel | all
python main.py --no-external      # ignore le cache réseau, utile hors-ligne
```

Chaque étape est idempotente et écrit dans `data/processed/`, ce qui permet à chacun de ne relancer que sa partie pendant les trois jours.

---

## 7. Répartition

Deux chantiers qui ne se touchent que via **deux contrats** : le format long (A → B) et des DataFrames de résultats au schéma figé (B → A). Personne n'édite le fichier de l'autre.

### 7.1 Périmètres

| | **A — Données → Classeur** | **B — Prévision & environnement** |
|---|---|---|
| **Question portée** | « Les données sont-elles fiables, et le client peut-il s'en servir ? » | « Peut-on prévoir, et qu'est-ce qui vient de l'extérieur ? » |
| **Modules** | `config.py`, `main.py`, `io/loaders.py`, `quality/*`, `features/*`, `stats/descriptive.py`, `excel/*`, `templates/` | `io/external.py`, `forecast/*`, `stats/seasonality.py`, `stats/variability.py`, `viz/plots.py` |
| **Tests** | `test_calendar.py`, `test_reconciliation.py` | `test_backtest.py` |
| **`settings.yaml`** | chemins, groupes ATC, seuils qualité | horizon, fenêtre de backtest, sources externes |

Logique du découpage : A tient les deux bouts du pipeline (entrée et sortie), B tout ce qui est analytique. `seasonality` et `variability` sont chez B parce qu'ils alimentent directement les modèles (indices saisonniers) et que le stock de sécurité se dimensionne mieux à partir de l'erreur de prévision qu'à partir du seul CV.

### 7.2 Les contrats d'interface

**A → B** (livré par A dès **J1 midi**, même sous forme de stub) :

```python
load_all(settings) -> pd.DataFrame                      # format long, §3
aggregate(df, granularity: str) -> pd.DataFrame         # "D" | "W" | "M"
last_complete_month(df) -> pd.Period                    # calculé, jamais en dur
```

**B → A** (schémas figés J1, contenu livré au fil de l'eau) :

| DataFrame | Colonnes |
|---|---|
| `seasonal_profile` | `atc`, `dimension` (`month`/`weekday`/`hour`), `key`, `index` |
| `variability` | `atc`, `cv`, `safety_stock` |
| `backtest_results` | `atc`, `model`, `mae`, `mape`, `mase`, `gain_vs_baseline` |
| `forecast_next` | `atc`, `month`, `yhat`, `model`, `verdict` (`oui`/`non`) |
| `external_effect` | `atc`, `variable`, `corr`, `delta_mase` |

A écrit chaque DataFrame dans une feuille via `sheets.py` sans connaître son contenu : si B ajoute un modèle, rien ne change côté A.

### 7.3 Planning et points de synchro

| | A | B | Synchro |
|---|---|---|---|
| **J1 matin** | Squelette du repo, `config.py`, stub `load_all` sur `Monthly.csv` | Fetch + cache donnée externe, `baselines.py`, `metrics.py` (sur le stub) | **09h** : on fige ensemble §3 et §7.2 |
| **J1 après-midi** | `schema.py`, `reconciliation.py`, `checks.py` | `backtest.py` + `test_backtest.py` | **18h** : A annonce le dernier mois complet → B fixe la cible |
| **J2 matin** | `report.py`, `features/*`, `descriptive.py` | `models.py` (ETS, SARIMA), `seasonality.py` | |
| **J2 après-midi** | `excel/*` + template, `main.py --stage` | Régression exogène, `variability.py`, `external_effect` | **17h** : premier `python main.py` de bout en bout |
| **J3 matin** | Test depuis un clone vierge, README | `viz/plots.py`, figures pour les decks et le mémo | **11h** : gel du code, on passe à la rédaction |

### 7.4 Règles de travail

- **Une branche par module** (`feat/reconciliation`, `feat/backtest`…), PR vers `main`, **relue par l'autre** avant merge : chacun connaît le code de l'autre pour l'oral.
- **Commits petits et fréquents**, plusieurs fois par jour chacun : l'historique est noté.
- **Le stub d'abord** : quand on attend l'autre, on code contre un stub au bon schéma, on ne bloque jamais.
- Toute modification d'un contrat (§3, §7.2) se décide **à deux** et se répercute dans ce document.

---

## 8. `.gitignore` minimal

```
__pycache__/
*.py[cod]
.venv/
venv/
.ipynb_checkpoints/
.DS_Store
data/processed/
output/
```

Les exports `data/raw/`, le cache `data/external/` et le template `templates/` sont **commités** : sans eux le clone vierge ne tourne pas.
