class BiologicalImpactEngine:

    REGLES_CULTURES = {
        "Tomate": {
            "temp_max_critique": 34.0,
            "hum_sol_min": 22.0,
            "sensibilite": "Haute",
        },
        "Maïs": {
            "temp_max_critique": 36.0,
            "hum_sol_min": 18.0,
            "sensibilite": "Moyenne",
        },
        "Blé": {
            "temp_max_critique": 32.0,
            "hum_sol_min": 15.0,
            "sensibilite": "Faible",
        },
    }

    @classmethod
    def evaluer_sante_plante(
        cls, culture: str, temp_air: float, humidite_sol: float
    ):
        params = cls.REGLES_CULTURES.get(
            culture, cls.REGLES_CULTURES["Tomate"]
        )

        risques = []
        score_sante = 100

        # Risque 1 : Flétrissement par stress hydrique
        if humidite_sol < params["hum_sol_min"]:
            score_sante -= 40
            if temp_air >= params["temp_max_critique"]:
                risques.append(
                    f"🚨 CRITIQUE : Risque de flétrissement irréversible des {culture}s sous 12h (Sol à {humidite_sol}% + Chaleur à {temp_air}°C) !"
                )
            else:
                risques.append(
                    f"⚠️ WARNING : Flétrissement léger observé. Le sol est sous le seuil critique de {params['hum_sol_min']}%."
                )

        # Risque 2 : Stress Thermique / Coulure des fleurs
        if temp_air >= params["temp_max_critique"]:
            score_sante -= 25
            risques.append(
                f"🔥 Stress thermique : Température excessive ({temp_air}°C). Risque de chute des fleurs et arrêt de croissance."
            )

        if not risques:
            risques.append(
                f"✅ Culture en excellente santé ({score_sante}%). Paramètres environnementaux optimaux."
            )

        return {"score_sante": max(0, score_sante), "diagnostics": risques}