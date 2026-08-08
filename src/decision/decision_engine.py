"""
decision_engine.py
===================

Point central du diagnostic d'une zone : combine plusieurs sources
d'information pour répondre à "faut-il arroser, et pourquoi ?" de façon
explicable — c'est directement la réponse à "sur quoi sont basées les
prédictions ?" :

    1. Météo réelle (Open-Meteo) pour la ville de la zone
    2. Probabilité d'arrosage donnée par le réseau de neurones (MLP), à
       partir de : humidité du sol (saisie manuellement, pas de capteur
       physique), météo réelle, type de sol, catégorie de culture
    3. État de santé de la culture (risque de flétrissement/stress
       thermique) via des seuils agronomiques par culture
    4. Conseils phytosanitaires à partir des conditions météo réelles

Cette fonction est volontairement SANS EFFET DE BORD (elle ne modifie ni
base de données ni réservoir) : c'est à l'appelant (voir backend/api.py)
de décider quoi faire du diagnostic (ex : consommer le réservoir si le
mode automatique est activé pour cette zone).
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from meteo import obtenir_meteo
from dataset import entree_unique, categorie_large
from predict import _charger_artefacts
from biologie.biological_impact import BiologicalImpactEngine
from conseil.Conseil import ConseilsPhytosanitaires

def diagnostic_complet(zone: dict) -> dict:
    """
    zone : dict avec au minimum nom, ville, type_sol, culture_specifique,
    humidite_sol (voir backend/db.py::obtenir_zone).
    """
    # 1. Météo réelle pour la ville de la zone
    meteo = obtenir_meteo(zone["ville"])
    if meteo is None:
        return {
            "erreur": f"Ville '{zone['ville']}' introuvable ou météo indisponible. "
                      f"Vérifie la connexion internet ou le nom de la ville."
        }

    temp_air = meteo["temperature_actuelle"]
    humidite_air = meteo["humidite_air_actuelle"]
    pluie_prevue_mm = meteo["pluie_aujourdhui_mm"]
    humidite_sol = zone["humidite_sol"]
    culture_specifique = zone["culture_specifique"]
    categorie_ml = categorie_large(culture_specifique)

    # 2. Probabilité d'arrosage (réseau de neurones)
    model, scaler = _charger_artefacts()
    X = entree_unique(humidite_sol, temp_air, humidite_air, pluie_prevue_mm,
                       zone["type_sol"], categorie_ml)
    proba = float(model.predict_proba(scaler.transform(X))[0, 1])

    if proba > 0.6:
        decision, volume_litres = "ARROSER", 20.0 * (1 + zone.get("surface_hectares", 1.0) / 10)
        raison = (f"Sol à {humidite_sol:.0f}% (sous le seuil), {temp_air:.0f}°C, "
                  f"{pluie_prevue_mm:.0f}mm de pluie prévue.")
    elif proba > 0.4:
        decision, volume_litres = "SURVEILLER", 0.0
        raison = "Conditions à la limite : à surveiller dans les prochaines heures."
    else:
        decision, volume_litres = "CONSERVER", 0.0
        raison = "Humidité du sol satisfaisante compte tenu des conditions actuelles."

    # 3. Santé de la culture (flétrissement, stress thermique)
    sante = BiologicalImpactEngine.evaluer_sante_plante(culture_specifique, temp_air, humidite_sol)

    # 4. Conseils phytosanitaires + besoin de traitement
    conseils = ConseilsPhytosanitaires.generer_conseils_regionaux(
        zone.get("region") or zone["ville"], temp_air, humidite_air, culture_specifique
    )
    besoin_traitement, raison_traitement = ConseilsPhytosanitaires.necessite_traitement(
        temp_air, humidite_air
    )

    return {
        "zone_nom": zone["nom"],
        "meteo_temps_reel": {
            "ville": meteo["ville"],
            "temperature": temp_air,
            "humidite_air": humidite_air,
            "pluie_aujourdhui_mm": pluie_prevue_mm,
            "pluie_totale_72h_mm": meteo["pluie_totale_72h_mm"],
        },
        "decision_arrosage": {
            "action": decision,
            "confiance": proba,
            "volume_litres_recommande": round(volume_litres, 1),
            "raison": raison,
        },
        "sante_culture": sante,
        "conseils_phytosanitaires": conseils,
        "traitement_recommande": {
            "necessaire": besoin_traitement,
            "raison": raison_traitement,
        },
    }
