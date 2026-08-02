"""
reservoir.py
============

Gère un réservoir d'eau virtuel pour la ferme : niveau actuel, consommation
par les arrosages, recharge par collecte d'eau de pluie (toiture/bâche).

Pourquoi un réservoir et pas juste "arroser ou pas" ?
--------------------------------------------------------
Sur le terrain, la vraie contrainte agricole n'est pas seulement "faut-il
arroser ?" mais aussi "est-ce que j'ai assez d'eau disponible ?". Un
réservoir donne un enjeu concret : si le niveau est bas, l'app doit le
signaler avant que l'agriculteur ne se retrouve à sec en pleine canicule.

L'état du réservoir est géré côté interface (voir app.py, gr.State) pour
persister pendant la session sans base de données.
"""

from dataclasses import dataclass

CAPACITE_DEFAUT_L = 5000.0          # capacité totale du réservoir (ferme moyenne)
SURFACE_CAPTAGE_DEFAUT_M2 = 150.0    # surface de toiture/bâche qui collecte la pluie
EFFICACITE_COLLECTE = 0.8            # 80% de la pluie tombée est effectivement récupérée
SEUIL_ALERTE_PCT = 20.0              # en dessous de 20%, on alerte l'agriculteur


@dataclass
class EtatReservoir:
    capacite_l: float = CAPACITE_DEFAUT_L
    niveau_l: float = CAPACITE_DEFAUT_L * 0.6  # on démarre à 60% par défaut

    @property
    def niveau_pct(self) -> float:
        return 100 * self.niveau_l / self.capacite_l

    @property
    def en_alerte(self) -> bool:
        return self.niveau_pct < SEUIL_ALERTE_PCT


def consommer(etat: EtatReservoir, litres: float) -> tuple[EtatReservoir, str]:
    """Retire de l'eau du réservoir pour un arrosage. Ne descend jamais sous 0
    (le manque est signalé plutôt que de créer un niveau négatif)."""
    manque = max(0.0, litres - etat.niveau_l)
    nouveau_niveau = max(0.0, etat.niveau_l - litres)
    nouvel_etat = EtatReservoir(capacite_l=etat.capacite_l, niveau_l=nouveau_niveau)

    if manque > 0:
        message = (f"⚠️ Réservoir insuffisant : il manquait {manque:.0f} L "
                    f"pour cet arrosage de {litres:.0f} L.")
    else:
        message = f"💧 {litres:.0f} L prélevés. Niveau restant : {nouvel_etat.niveau_l:.0f} L."

    return nouvel_etat, message


def recharger_pluie(etat: EtatReservoir, pluie_mm: float,
                     surface_captage_m2: float = SURFACE_CAPTAGE_DEFAUT_M2) -> tuple[EtatReservoir, str]:
    """Simule la collecte d'eau de pluie sur une surface de toiture/bâche.
    1 mm de pluie sur 1 m² = 1 litre collecté (avant efficacité de collecte)."""
    litres_collectes = pluie_mm * surface_captage_m2 * EFFICACITE_COLLECTE
    nouveau_niveau = min(etat.capacite_l, etat.niveau_l + litres_collectes)
    debordement = max(0.0, etat.niveau_l + litres_collectes - etat.capacite_l)
    nouvel_etat = EtatReservoir(capacite_l=etat.capacite_l, niveau_l=nouveau_niveau)

    message = f"🌧️ {litres_collectes:.0f} L collectés grâce à la pluie."
    if debordement > 0:
        message += f" Réservoir plein ({debordement:.0f} L perdus par débordement)."

    return nouvel_etat, message


def recharger_manuellement(etat: EtatReservoir, litres: float) -> EtatReservoir:
    """Remplissage manuel (ex : citerne apportée par camion)."""
    nouveau_niveau = min(etat.capacite_l, etat.niveau_l + litres)
    return EtatReservoir(capacite_l=etat.capacite_l, niveau_l=nouveau_niveau)
