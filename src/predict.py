"""
predict.py
==========

Charge le modèle déjà entraîné (voir train.py) et expose une fonction
`predire_arrosage(...)` prête à l'emploi pour l'app Gradio et pour la
simulation de capteur virtuel.

Contrairement à l'ancienne version (Model.py), ce module NE RÉ-ENTRAÎNE PAS
le réseau de neurones à chaque import : il charge simplement le modèle déjà
sauvegardé par train.py.
"""

import os
import sys

import joblib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dataset import entree_unique

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "irrigation_model.joblib")
SCALER_PATH = os.path.join(MODELS_DIR, "scaler.joblib")

_model = None
_scaler = None


def _charger_artefacts():
    """Charge le modèle et le scaler une seule fois (mise en cache)."""
    global _model, _scaler

    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(
            "Modèle introuvable. Lance d'abord l'entraînement :\n"
            "    python src/train.py"
        )

    if _model is None:
        _model = joblib.load(MODEL_PATH)

    if _scaler is None:
        _scaler = joblib.load(SCALER_PATH)

    return _model, _scaler


def predire_arrosage(humidite_sol, temperature_air, humidite_air,
                      pluie_prevue_mm, type_sol, type_culture):
    """Retourne un message lisible avec la décision d'arrosage et la
    confiance du modèle, à partir des mesures fournies."""
    model, scaler = _charger_artefacts()

    X = entree_unique(humidite_sol, temperature_air, humidite_air,
                       pluie_prevue_mm, type_sol, type_culture)
    X_scaled = scaler.transform(X)

    proba = model.predict_proba(X_scaled)[0, 1]

    if proba > 0.5:
        return f"🔴 Arrosage REQUIS (confiance : {proba:.0%})"
    return f"🟢 Sol stable, pas besoin d'arroser (confiance : {1 - proba:.0%})"
