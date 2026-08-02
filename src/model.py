"""
model.py
========

Définition du modèle de classification : un réseau de neurones multicouche
(MLP), via scikit-learn plutôt que PyTorch.

Pourquoi scikit-learn plutôt que PyTorch ?
--------------------------------------------
PyTorch pèse ~150 Mo installés et peut littéralement échouer à l'installation
sous Windows à cause de chemins de fichiers trop longs (notamment avec le
Python du Microsoft Store) — ce qui force à modifier le registre Windows et
redémarrer. Pour un projet de cette taille (dataset de 2000 lignes, réseau
à 3 petites couches), c'est disproportionné, surtout si le projet doit être
installé facilement par d'autres personnes (jury, collègues).

Un MLPClassifier scikit-learn repose sur les mêmes concepts fondamentaux
(couches cachées, activation ReLU, rétropropagation, descente de gradient
Adam) et reste un "vrai" réseau de neurones — juste sans le poids ni les
soucis d'installation de PyTorch.
"""

from sklearn.neural_network import MLPClassifier


def creer_modele(random_state: int = 42) -> MLPClassifier:
    """Crée un réseau de neurones multicouche (3 couches cachées 32-16-8),
    entraîné par rétropropagation (solver Adam) — architecture équivalente
    en esprit à la version PyTorch initiale.

    early_stopping=True réserve automatiquement une partie des données
    d'entraînement pour surveiller le surapprentissage et arrêter dès que
    la performance cesse de progresser (rôle similaire au Dropout de la
    version PyTorch initiale)."""
    return MLPClassifier(
        hidden_layer_sizes=(32, 16, 8),
        activation="relu",
        solver="adam",
        alpha=1e-2,               # régularisation L2
        learning_rate_init=0.005,
        max_iter=500,
        early_stopping=True,        # arrêt automatique anti-surapprentissage
        random_state=random_state,
    )
