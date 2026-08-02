"""
generate_dataset.py
====================

Génère un jeu de données SYNTHÉTIQUE mais réaliste pour le projet
"Irrigation Automatique Intelligente".

Pourquoi générer nous-mêmes le dataset plutôt que d'en télécharger un ?
------------------------------------------------------------------------
- Aucun capteur physique n'est disponible : on simule leurs mesures.
- On garde un contrôle total sur les règles agronomiques qui définissent
  "quand faut-il arroser ?", ce qui rend le projet explicable devant un
  jury (on peut justifier chaque variable et chaque seuil).
- Le fichier généré est un simple CSV, donc lisible par un humain
  (Excel, LibreOffice, éditeur de texte...), contrairement à un modèle
  ou un fichier binaire.

Variables générées
-------------------
- humidite_sol        (%)   : mesure du capteur d'humidité du sol
- temperature_air      (°C)  : température ambiante
- humidite_air         (%)   : hygrométrie de l'air
- pluie_prevue_mm       (mm)  : précipitations prévues dans les 24h
- type_sol             (cat) : Sableux / Limoneux / Argileux
- type_culture          (cat) : Maraîchage / Céréales / Arboriculture
- besoin_arrosage        (0/1) : cible principale à prédire (classification)
- quantite_eau_litres_m2 (L/m²): estimation du volume d'eau nécessaire
                                  (utile pour l'analyse exploratoire et une
                                  future extension en régression)

La cible n'est pas un simple seuil déterministe : elle combine plusieurs
règles agronomiques + un bruit aléatoire, pour éviter un jeu de données
"trop parfait" (parfaitement séparable), ce qui serait irréaliste et
mènerait à un modèle qui semble "trop bon pour être vrai" devant un jury.

Utilisation
-----------
    python data/generate_dataset.py --n 2000

Produit : data/irrigation_dataset.csv
"""

import argparse
import os

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Paramètres agronomiques (facilement justifiables à l'oral)
# ------------------------------------------------------------------

# Rétention d'eau selon le type de sol : plus le coefficient est élevé,
# plus le sol retient l'eau longtemps (donc moins besoin d'arroser souvent).
RETENTION_SOL = {
    "Sableux": -8.0,    # draine vite -> assèche vite -> besoin d'arrosage plus fréquent
    "Limoneux": 0.0,    # référence
    "Argileux": +8.0,   # retient l'eau -> besoin d'arrosage moins fréquent
}

# Besoin en eau de base selon le type de culture (L/m² par arrosage).
BESOIN_BASE_CULTURE = {
    "Maraîchage": 6.0,      # légumes : racines superficielles, besoin fréquent
    "Céréales": 4.0,        # plus résistantes à la sécheresse
    "Arboriculture": 8.0,   # arbres fruitiers : arrosage plus rare mais plus copieux
}


def generer_dataset(n_samples: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    types_sol = rng.choice(list(RETENTION_SOL.keys()), size=n_samples)
    types_culture = rng.choice(list(BESOIN_BASE_CULTURE.keys()), size=n_samples)

    # --- Variables mesurées / prévues (capteurs simulés) ---
    humidite_sol = np.clip(rng.normal(45, 22, n_samples), 2, 100)
    temperature_air = np.clip(rng.normal(26, 7, n_samples), 8, 45)
    humidite_air = np.clip(rng.normal(55, 18, n_samples), 10, 100)

    # La pluie est rare : la majorité des jours sont secs (loi exponentielle),
    # avec un plafond réaliste à 40 mm/24h.
    pluie_prevue_mm = np.clip(rng.exponential(3.0, n_samples), 0, 40)

    # --- Score agronomique combiné (plus il est élevé, plus il faut arroser) ---
    retention = np.array([RETENTION_SOL[t] for t in types_sol])

    score = (
        (50 - humidite_sol) * 1.1          # sol sec -> score monte
        + (temperature_air - 25) * 1.3      # chaleur -> évaporation -> score monte
        - (humidite_air - 50) * 0.4         # air humide -> moins d'évaporation
        - pluie_prevue_mm * 3.5             # pluie prévue -> inutile d'arroser
        + retention                          # effet du type de sol
    )

    # Bruit aléatoire : conditions non modélisées (vent, ombrage, erreurs
    # de capteur...). Sans ce bruit, le jeu de données serait parfaitement
    # séparable, ce qui n'arrive jamais avec de vraies mesures.
    bruit = rng.normal(0, 12, n_samples)
    score_bruite = score + bruit

    # Probabilité d'arrosage via une fonction logistique du score
    proba_arrosage = 1 / (1 + np.exp(-score_bruite / 15))
    besoin_arrosage = (rng.uniform(0, 1, n_samples) < proba_arrosage).astype(int)

    # --- Quantité d'eau recommandée (0 si pas d'arrosage nécessaire) ---
    besoin_base = np.array([BESOIN_BASE_CULTURE[c] for c in types_culture])
    quantite_eau = besoin_base * (1 + np.clip(score, 0, None) / 40)
    quantite_eau = np.where(besoin_arrosage == 1, quantite_eau, 0.0)
    quantite_eau = np.round(quantite_eau, 2)

    df = pd.DataFrame({
        "humidite_sol": np.round(humidite_sol, 1),
        "temperature_air": np.round(temperature_air, 1),
        "humidite_air": np.round(humidite_air, 1),
        "pluie_prevue_mm": np.round(pluie_prevue_mm, 1),
        "type_sol": types_sol,
        "type_culture": types_culture,
        "besoin_arrosage": besoin_arrosage,
        "quantite_eau_litres_m2": quantite_eau,
    })

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère le dataset d'irrigation.")
    parser.add_argument("--n", type=int, default=2000, help="Nombre de lignes à générer")
    parser.add_argument("--seed", type=int, default=42, help="Graine aléatoire (reproductibilité)")
    args = parser.parse_args()

    df = generer_dataset(args.n, args.seed)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "irrigation_dataset.csv")
    df.to_csv(out_path, index=False)

    print(f"Dataset généré : {len(df)} lignes -> {out_path}")
    print(f"Répartition besoin_arrosage :\n{df['besoin_arrosage'].value_counts(normalize=True).round(3)}")
