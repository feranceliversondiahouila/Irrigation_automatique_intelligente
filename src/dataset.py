"""
dataset.py
==========

Prépare les données pour l'entraînement ET pour l'inférence, en garantissant
que les deux utilisent EXACTEMENT le même prétraitement (même ordre de
colonnes, mêmes catégories encodées). C'est une source d'erreurs classique
quand ce code est dupliqué (comme c'était le cas entre Model.py et
simulation_capteur.py dans la version précédente) : on centralise ici.
"""

import os

import numpy as np
import pandas as pd

# Colonnes numériques (utilisées telles quelles, puis normalisées)
COLONNES_NUMERIQUES = ["humidite_sol", "temperature_air", "humidite_air", "pluie_prevue_mm"]

# Catégories figées : l'ordre doit rester identique entre entraînement et
# inférence, sinon les colonnes one-hot ne correspondraient plus aux mêmes
# poids appris par le modèle.
CATEGORIES_SOL = ["Sableux", "Limoneux", "Argileux"]
CATEGORIES_CULTURE = ["Maraîchage", "Céréales", "Arboriculture"]

CIBLE = "besoin_arrosage"

DATA_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "irrigation_dataset.csv")


def charger_dataset(csv_path: str = DATA_CSV) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def encoder_categorielles(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode type_sol / type_culture avec des catégories figées."""
    df = df.copy()
    df["type_sol"] = pd.Categorical(df["type_sol"], categories=CATEGORIES_SOL)
    df["type_culture"] = pd.Categorical(df["type_culture"], categories=CATEGORIES_CULTURE)
    df = pd.get_dummies(df, columns=["type_sol", "type_culture"], prefix=["sol", "culture"])
    return df


def colonnes_features() -> list:
    """Liste figée et ordonnée de toutes les colonnes d'entrée du modèle."""
    return (
        COLONNES_NUMERIQUES
        + [f"sol_{c}" for c in CATEGORIES_SOL]
        + [f"culture_{c}" for c in CATEGORIES_CULTURE]
    )


def construire_matrice_features(df: pd.DataFrame) -> np.ndarray:
    """Transforme un DataFrame brut (colonnes originales) en matrice X prête
    pour le scaler / le modèle, avec un ordre de colonnes garanti."""
    df_encode = encoder_categorielles(df)
    for col in colonnes_features():
        if col not in df_encode.columns:
            df_encode[col] = 0
    return df_encode[colonnes_features()].astype(float).values


def entree_unique(humidite_sol, temperature_air, humidite_air, pluie_prevue_mm,
                   type_sol, type_culture) -> np.ndarray:
    """Construit la matrice de features (1 ligne) pour une prédiction ponctuelle,
    utilisée par l'app Gradio et la simulation de capteur."""
    df = pd.DataFrame([{
        "humidite_sol": humidite_sol,
        "temperature_air": temperature_air,
        "humidite_air": humidite_air,
        "pluie_prevue_mm": pluie_prevue_mm,
        "type_sol": type_sol,
        "type_culture": type_culture,
    }])
    return construire_matrice_features(df)
