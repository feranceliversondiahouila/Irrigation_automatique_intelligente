"""
conseil.py
==========

Génère des conseils phytosanitaires à partir des conditions météo réelles
(pas d'une recherche internet en direct — voir le README pour l'explication
de ce choix). Les règles utilisées sont des repères agronomiques connus :
chaleur sèche → acariens/pucerons, chaleur humide → champignons/mildiou.
"""


class ConseilsPhytosanitaires:

    @staticmethod
    def generer_conseils_regionaux(region: str, temp_air: float, humidite_air: float, culture: str) -> list:
        conseils = []

        if temp_air > 28 and humidite_air < 40:
            conseils.append(
                f"🐛 Alerte ravageurs ({region}) : les conditions chaudes et sèches favorisent "
                f"la prolifération d'acariens et de pucerons sur les {culture.lower()}s. "
                f"Inspection recommandée sous les feuilles."
            )
        elif humidite_air > 75 and temp_air > 20:
            conseils.append(
                f"🍄 Alerte mildiou / champignons : humidité élevée ({humidite_air:.0f}%). "
                f"Risque fort de maladies cryptogamiques. Éviter d'arroser le feuillage."
            )

        if temp_air > 30:
            conseils.append(
                "💡 Conseil agro-écologique : un paillage au pied des plants limiterait "
                "l'évaporation et conserverait l'humidité du sol."
            )

        return conseils

    @staticmethod
    def necessite_traitement(temp_air: float, humidite_air: float) -> tuple:
        """Détermine si les conditions actuelles justifient un traitement
        phytosanitaire préventif (utilisé pour le mode automatique).
        Retourne (bool, raison)."""
        if temp_air > 28 and humidite_air < 40:
            return True, "Conditions favorables aux acariens/pucerons (chaleur sèche)."
        if humidite_air > 75 and temp_air > 20:
            return True, "Conditions favorables aux champignons/mildiou (chaleur humide)."
        return False, "Conditions actuelles peu propices aux ravageurs."
