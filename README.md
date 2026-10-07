# Rush 2 — Pharmaceutical Sales Analysis

```bash
pip install -r requirements.txt
python main.py
```

Architecture : voir [ARCHITECTURE.MD](ARCHITECTURE.MD).

## Qui a fait quoi

| Membre | Rôle | Modules |
|---|---|---|
| Enzo | A — Données → Classeur | `io/loaders`, `quality/*`, `features/*`, `stats/descriptive`, `excel/*` |
| Seif | B — Prévision & environnement | `io/external`, `forecast/*`, `stats/seasonality`, `stats/variability`, `viz/*` |
