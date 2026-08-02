from biologie.biological_impact import BiologicalImpactEngine
from conseil.Conseil import ConseilsPhytosanitaires
from meteo import MeteoService
from reservoir import GestionReservoir  # Module de gestion des stocks


def diagnostic_complet(
    ville: str,
    culture: str,
    humidite_sol: float,
    niveau_reservoir_pct: float,
    capacite_reservoir_l=5000,
):
    # 1. Météo dynamique en temps réel
    geo = MeteoService.geolocaliser(ville)
    if not geo:
        return {"erreur": f"Ville '{ville}' introuvable."}

    meteo = MeteoService.obtenir_meteo_temps_reel(geo["lat"], geo["lon"])

    # 2. Impact biologique / Flétrissement
    impact = BiologicalImpactEngine.evaluer_sante_plante(
        culture, meteo["temperature"], humidite_sol
    )

    # 3. Prise de décision d'arrosage
    decision = "CONSERVER"
    volume_rec = 0
    raison = ""

    if humidite_sol < 25:
        if meteo["pluie_prevue_3j"] >= 8.0:
            decision = "ANNULER"
            raison = f"Sol sec ({humidite_sol}%), mais pluie importante prévue sous 72h ({meteo['pluie_prevue_3j']} mm)."
        else:
            decision = "ARROSER"
            volume_rec = 30 if culture == "Maïs" else 20
            if meteo["temperature"] > 32:
                volume_rec *= 1.25  # +25% si canicule
            raison = f"Sol sous le seuil critique + Forte température ({meteo['temperature']}°C)."
    else:
        raison = "Niveau d'humidité du sol satisfaisant."

    # 4. Impact Réservoir
    res_info = GestionReservoir.calculer_etat(
        niveau_reservoir_pct, volume_rec, meteo["pluie_actuelle"]
    )

    # 5. Recommandations phytosanitaires
    conseils = ConseilsPhytosanitaires.generer_conseils_regionaux(
        geo["region"], meteo["temperature"], meteo["humidite_air"], culture
    )

    return {
        "localisation": geo,
        "meteo_temps_reel": meteo,
        "sante_culture": impact,
        "decision_arrosage": {
            "action": decision,
            "volume_litres": round(volume_rec, 1),
            "raison": raison,
        },
        "reservoir": res_info,
        "conseils_phytosanitaires": conseils,
    }