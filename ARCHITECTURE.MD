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
4. **`Weekly` démarre le dimanche** (`1/5/2014`). À confirmer avant toute comparaison avec une réagrégation ISO (lundi), sinon les écarts seront des artefacts.
5. **Octobre 2019 probablement incomplet.** `checks.py` le détermine, ne le suppose pas, et l'exclut des stats mensuelles et de l'évaluation des prévisions.

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

Elle découle de l'architecture — les trois chantiers ne se touchent que via le format long et `settings.yaml`.

| | Périmètre code |
|---|---|
| **Personne 1 — Data/Pipeline** | `io/loaders.py`, `quality/*`, `features/*`, `main.py` |
| **Personne 2 — Modélisation** | `forecast/*`, `io/external.py` |
| **Personne 3 — Outil & comm** | `excel/*`, `templates/`, `stats/*`, `viz/plots.py` |

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
