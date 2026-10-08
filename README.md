# Rush 2 — Pharmaceutical Sales Analysis

Analyse de 6 ans d'exports de caisse d'une officine (8 groupes ATC, janvier 2014 → octobre 2019) : fiabilisation des données, statistiques descriptives, prévision du mois suivant, donnée publique externe et outil Excel autonome.

## Lancer le projet

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python main.py                     # pipeline complet, ~40 s
```

| Option | Effet |
|---|---|
| `--stage quality` | chargement des 4 exports, réconciliation, nettoyage, état des données |
| `--stage stats` | ventes mensuelles, volumes et parts, tendance annuelle |
| `--stage forecast` | backtest, prévision, saisonnalité, variabilité, effet externe, figures |
| `--stage excel` | génération du classeur |
| `--no-external` | n'utilise que le cache `data/external/`, aucun accès réseau |

Chaque étape lit les sorties de la précédente dans `data/processed/` et peut être relancée seule. Tests : `python -m pytest`.

## Ce que produit le pipeline

| Sortie | Contenu |
|---|---|
| `output/Analyse_Pharma.xlsx` | Synthèse, **Outil** (période + groupes ATC au choix, sans macro), Statistiques, Saisonnalité, Prévisions, État des données, Data |
| `output/figures/` | saisonnalité, profils jour/heure, backtest et grippe pour N02BE et R03 |
| `data/processed/` | tables intermédiaires (ignorées par Git) |

Le classeur est généré à partir du modèle `templates/outil_pharma.xlsx` : Python ne réécrit que ses tableaux nommés, l'outil et ses formules ne sont jamais modifiés.

## Principaux constats sur les données

- Horaire, journalier et hebdomadaire concordent exactement une fois réagrégés.
- **L'export mensuel est incohérent** (45 cellules sur 560 en écart, jusqu'à +75 %) : il est écarté et recalculé depuis le journalier.
- Octobre 2019 ne couvre que 8 jours : exclu des statistiques mensuelles et de la prévision.
- Aucun jour manquant, doublon ni valeur négative ; les quantités décimales sont conservées (unité non documentée).

Le détail de chaque décision est dans la feuille « État des données ».

## Structure

```
main.py               point d'entrée unique
config/settings.yaml  chemins, groupes ATC, seuils, paramètres de prévision, sources externes
data/raw/             les 4 exports fournis
data/external/        cache de la donnée publique (Réseau Sentinelles)
templates/            modèle Excel contenant l'outil
src/pharma/           io · quality · features · stats · forecast · excel · viz
tests/                tests unitaires et anti-fuite du backtest
```

Documentation : [MISSION.md](MISSION.md) (cadrage), [ARCHITECTURE.MD](ARCHITECTURE.MD) (code), [TACHES.md](TACHES.md) (répartition), [context.MD](context.MD) (sujet et dictionnaire des données).

## Qui a fait quoi

| Membre | Rôle | Code | Hors code |
|---|---|---|---|
| Enzo | A — Données → Classeur | `io/loaders`, `quality/*` (schéma, réconciliation, contrôles, nettoyage), `features/*`, `stats/descriptive`, `excel/*`, template Excel, `main.py` | Mémo partie 2 (risques du partage), deck Propriétaire |
| Seif | B — Prévision & environnement | `io/external`, `forecast/*` (baselines, ETS, SARIMA, backtest, métriques, effet externe), `stats/seasonality`, `stats/variability`, `viz/plots`, tests | Mémo partie 1 (prévision), deck Manager |
| Ensemble | | Architecture, contrats d'interface, revues de PR | Deck Pharmacien acheteur, répétition des oraux |
