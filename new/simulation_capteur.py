"""
simulation_capteur.py
======================

Simule un capteur virtuel qui envoie des mesures toutes les 5 secondes,
et affiche la décision d'arrosage prise par le modèle déjà entraîné
(voir src/train.py). Pratique pour une démonstration live devant un jury.

Lancer :
    python simulation_capteur.py
"""

import os
import random
import sys
import time

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from predict import predire_arrosage
from dataset import CATEGORIES_SOL, CATEGORIES_CULTURE

if __name__ == "__main__":
    print("📡 Simulation de capteur virtuel — Ctrl+C pour arrêter\n")
    try:
        while True:
            humidite_sol = round(random.uniform(5.0, 95.0), 1)
            temperature_air = round(random.uniform(10.0, 42.0), 1)
            humidite_air = round(random.uniform(20.0, 95.0), 1)
            pluie_prevue = round(random.uniform(0.0, 15.0), 1)
            type_sol = random.choice(CATEGORIES_SOL)
            type_culture = random.choice(CATEGORIES_CULTURE)

            resultat = predire_arrosage(
                humidite_sol, temperature_air, humidite_air,
                pluie_prevue, type_sol, type_culture,
            )

            print(f"🌡️ Sol {humidite_sol}% | Air {temperature_air}°C / {humidite_air}% | "
                  f"Pluie {pluie_prevue}mm | {type_sol} / {type_culture}")
            print(f"   -> {resultat}\n")

            time.sleep(5)
    except KeyboardInterrupt:
        print("\nSimulation arrêtée par l'utilisateur.")
