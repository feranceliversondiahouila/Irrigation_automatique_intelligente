class ConseilsPhytosanitaires:

    @staticmethod
    def generer_conseils_regionaux(
        region: str, temp_air: float, humidite_air: float, culture: str
    ):
        conseils = []

        # Risques d'insectes (ex: Pucerons, Acariens sous chaleur sèche)
        if temp_air > 28 and humidite_air < 40:
            conseils.append(
                f"🐛 **Alerte Ravageurs ({region})** : Les conditions chaudes et sèches favorisent la prolifération rapide des acariens et pucerons sur le {culture}. Inspection recommandée sous les feuilles."
            )

        # Risques Fongiques (Maladies/Champignons par forte humidité + chaleur)
        elif humidite_air > 75 and temp_air > 20:
            conseils.append(
                f"🍄 **Alerte Mildiou / Champignons** : Humidité élevée ({humidite_air}%). Risque fort de cryptogames. Éviter d'arroser le feuillage et appliquer un fongicide préventif si nécessaire."
            )

        # Recommandation de paillage
        if temp_air > 30:
            conseils.append(
                "💡 **Conseil Agro-écologique** : Installer un paillage au pied des plants pour limiter l'évaporation et conserver l'humidité du sol."
            )

        return conseils