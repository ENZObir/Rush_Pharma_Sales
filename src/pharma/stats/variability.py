"""Coefficient de variation et stock de sécurité, en quantités enregistrées par le logiciel."""

import numpy as np
import pandas as pd

VARIABILITY_COLUMNS = ["atc", "cv", "safety_stock"]


def variability(monthly: pd.DataFrame, forecast_errors: pd.DataFrame,
                z: float, lead_time_months: float) -> pd.DataFrame:
    """Sortie : VARIABILITY_COLUMNS. Contrat B → A.

    - cv : écart-type / moyenne des ventes mensuelles (mois complets, une colonne par ATC).
    - safety_stock : z × σ(erreurs du backtest du modèle retenu) × √(délai en mois).
      On dimensionne sur l'erreur de prévision et non sur σ des ventes : la part
      prévisible (saison, tendance) n'a pas à être couverte par du stock.
    `forecast_errors` : colonnes atc, error (réel − prévu), un ATC = son modèle retenu.
    """
    sigma = forecast_errors.groupby("atc")["error"].std()
    out = pd.DataFrame({"atc": monthly.columns.astype(str)})
    out["cv"] = (monthly.std() / monthly.mean()).to_numpy()
    out["safety_stock"] = z * sigma.reindex(out["atc"]).to_numpy() * np.sqrt(lead_time_months)
    return out[VARIABILITY_COLUMNS]
