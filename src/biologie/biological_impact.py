"""
biological_impact.py
=====================

Évalue "l'état de vie" de la culture d'une zone : risque de flétrissement
par manque d'eau, stress thermique, etc. — en fonction de la température
réelle et de l'humidité du sol de la zone.

Volontairement basé sur des seuils (pas un modèle ML) : ce sont des repères
agronomiques connus (température critique, humidité minimale du sol par
culture), faciles à justifier et à ajuster à l'oral.
"""


class BiologicalImpactEngine:

    # Seuils approximatifs par culture spécifique (à affiner avec de vraies
    # données terrain si le projet est poursuivi).
    REGLES_CULTURES = {
        "Tomate":          {"temp_max_critique": 34.0, "hum_sol_min": 22.0, "sensibilite": "Haute"},
        "Laitue":          {"temp_max_critique": 28.0, "hum_sol_min": 28.0, "sensibilite": "Haute"},
        "Pomme de terre":  {"temp_max_critique": 30.0, "hum_sol_min": 25.0, "sensibilite": "Moyenne"},
        "Maïs":            {"temp_max_critique": 36.0, "hum_sol_min": 18.0, "sensibilite": "Moyenne"},
        "Blé":             {"temp_max_critique": 32.0, "hum_sol_min": 15.0, "sensibilite": "Faible"},
        "Riz":             {"temp_max_critique": 35.0, "hum_sol_min": 35.0, "sensibilite": "Haute"},
        "Pommier":         {"temp_max_critique": 33.0, "hum_sol_min": 20.0, "sensibilite": "Moyenne"},
        "Oranger":         {"temp_max_critique": 38.0, "hum_sol_min": 20.0, "sensibilite": "Faible"},
        "Vigne":           {"temp_max_critique": 37.0, "hum_sol_min": 15.0, "sensibilite": "Faible"},
    }

    @classmethod
    def evaluer_sante_plante(cls, culture: str, temp_air: float, humidite_sol: float) -> dict:
        params = cls.REGLES_CULTURES.get(culture, cls.REGLES_CULTURES["Tomate"])

        risques = []
        score_sante = 100

        # Risque 1 : flétrissement par stress hydrique
        if humidite_sol < params["hum_sol_min"]:
            score_sante -= 40
            if temp_air >= params["temp_max_critique"]:
                risques.append(
                    f"🚨 CRITIQUE : risque de flétrissement des {culture.lower()}s sous 12h "
                    f"(sol à {humidite_sol:.0f}% + chaleur à {temp_air:.0f}°C) !"
                )
            else:
                risques.append(
                    f"⚠️ Flétrissement léger probable : le sol est sous le seuil critique "
                    f"de {params['hum_sol_min']:.0f}% pour cette culture."
                )

        # Risque 2 : stress thermique (chute de fleurs, arrêt de croissance)
        if temp_air >= params["temp_max_critique"]:
            score_sante -= 25
            risques.append(
                f"🔥 Stress thermique : température excessive ({temp_air:.0f}°C). "
                f"Risque de chute des fleurs et d'arrêt de croissance."
            )

        if not risques:
            risques.append(
                f"✅ Culture en bonne santé (score {max(0, score_sante)}%). "
                f"Conditions environnementales favorables."
            )

        return {
            "score_sante": max(0, score_sante),
            "sensibilite": params["sensibilite"],
            "diagnostics": risques,
        }
