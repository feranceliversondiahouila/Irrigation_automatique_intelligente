"""
train.py
========

Entraîne le modèle de classification (MLP scikit-learn), l'évalue sur un
jeu de TEST distinct, le compare à une baseline (RandomForest), puis
sauvegarde :

- models/irrigation_model.joblib : réseau de neurones entraîné
- models/scaler.joblib            : normalisation (StandardScaler)
- reports/metriques.txt            : accuracy / precision / recall / F1 des 2 modèles
- reports/matrice_confusion.png     : matrice de confusion du modèle MLP
- reports/courbe_apprentissage.png  : évolution de la perte pendant l'entraînement

Lancer depuis la racine du projet :
    python src/train.py
"""

import os
import sys

import joblib
import matplotlib
matplotlib.use("Agg")  # pas d'affichage interactif nécessaire (génère juste des fichiers)
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                              precision_score, recall_score)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dataset import CIBLE, charger_dataset, colonnes_features, construire_matrice_features
from model import creer_modele

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
sys.path.append(os.path.join(ROOT_DIR, "data"))
from generate_dataset import BESOIN_BASE_CULTURE

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def entrainer():
    print("1. Chargement du dataset...")
    df = charger_dataset()
    X = construire_matrice_features(df)
    y = df[CIBLE].values

    # Split train/test : on évalue sur des données JAMAIS vues à l'entraînement.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ------------------------------------------------------------
    # 2. Réseau de neurones multicouche (MLP - scikit-learn)
    # ------------------------------------------------------------
    print("2. Entraînement du réseau de neurones...")
    model = creer_modele()
    model.fit(X_train_scaled, y_train)
    historique_perte = model.loss_curve_

    # ------------------------------------------------------------
    # 3. Évaluation sur le jeu de TEST
    # ------------------------------------------------------------
    proba_test = model.predict_proba(X_test_scaled)[:, 1]
    pred_test = (proba_test > 0.5).astype(int)

    metriques_mlp = {
        "accuracy": accuracy_score(y_test, pred_test),
        "precision": precision_score(y_test, pred_test),
        "recall": recall_score(y_test, pred_test),
        "f1": f1_score(y_test, pred_test),
    }

    # ------------------------------------------------------------
    # 4. Baseline classique : RandomForest (pour comparaison)
    # ------------------------------------------------------------
    print("3. Entraînement de la baseline RandomForest (comparaison)...")
    rf = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
    rf.fit(X_train_scaled, y_train)
    pred_rf = rf.predict(X_test_scaled)

    metriques_rf = {
        "accuracy": accuracy_score(y_test, pred_rf),
        "precision": precision_score(y_test, pred_rf),
        "recall": recall_score(y_test, pred_rf),
        "f1": f1_score(y_test, pred_rf),
    }

    # ------------------------------------------------------------
    # 5. Sauvegarde des artefacts (modèle + scaler)
    # ------------------------------------------------------------
    joblib.dump(model, os.path.join(MODELS_DIR, "irrigation_model.joblib"))
    joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler.joblib"))
    joblib.dump(rf, os.path.join(MODELS_DIR, "random_forest.joblib"))
    print(f"Modèles sauvegardés dans : {MODELS_DIR}")

    # ------------------------------------------------------------
    # 6. Rapport texte (comparaison des 2 modèles, lisible pour le jury)
    # ------------------------------------------------------------
    rapport_path = os.path.join(REPORTS_DIR, "metriques.txt")
    with open(rapport_path, "w", encoding="utf-8") as f:
        f.write("RAPPORT D'ÉVALUATION — Irrigation Automatique Intelligente\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Taille du dataset : {len(df)} lignes "
                f"({len(X_train)} train / {len(X_test)} test)\n\n")

        for nom, m in [("Réseau de neurones multicouche (MLP)", metriques_mlp),
                       ("RandomForest (baseline classique)", metriques_rf)]:
            f.write(f"{nom}\n")
            f.write(f"  Accuracy  : {m['accuracy']:.3f}\n")
            f.write(f"  Precision : {m['precision']:.3f}\n")
            f.write(f"  Recall    : {m['recall']:.3f}\n")
            f.write(f"  F1-score  : {m['f1']:.3f}\n\n")

    print(f"Rapport de métriques : {rapport_path}")

    # ------------------------------------------------------------
    # 7. Graphiques (matrice de confusion + courbe d'apprentissage)
    # ------------------------------------------------------------
    cm = confusion_matrix(y_test, pred_test)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Pas d'arrosage", "Arrosage"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Pas d'arrosage", "Arrosage"])
    ax.set_xlabel("Prédiction"); ax.set_ylabel("Réalité")
    ax.set_title("Matrice de confusion — Réseau de neurones (MLP)")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "matrice_confusion.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(historique_perte)
    ax.set_xlabel("Époque"); ax.set_ylabel("Perte (Log Loss)")
    ax.set_title("Courbe d'apprentissage")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "courbe_apprentissage.png"), dpi=150)
    plt.close(fig)

    print(f"Graphiques sauvegardés dans : {REPORTS_DIR}")

    # ------------------------------------------------------------
    # 8. Économie d'eau : règle naïve vs annulation intelligente si pluie
    # ------------------------------------------------------------
    # Règle naïve classique ("Niveau 1" : un simple timer/seuil) : on arrose
    # dès que l'humidité du sol descend sous 30%, sans jamais regarder la
    # météo. On compare à la même règle, mais qui ANNULE l'arrosage si de
    # la pluie est prévue sous 24h (>= 5 mm) — c'est précisément la valeur
    # ajoutée de la météo réelle intégrée dans l'app (voir src/meteo.py).
    #
    # NB : on isole ici l'effet de la pluie uniquement (et pas l'effet du
    # type de sol/culture) pour avoir un chiffre honnête et facile à
    # défendre à l'oral : "sur nos données, X% des arrosages déclenchés par
    # un sol sec auraient été inutiles car de la pluie arrivait le lendemain".
    besoin_base = df["type_culture"].map(BESOIN_BASE_CULTURE)
    sol_sec = df["humidite_sol"] < 30

    arrosage_naif = sol_sec
    arrosage_intelligent = sol_sec & (df["pluie_prevue_mm"] < 5)

    eau_naive = (arrosage_naif.astype(int) * besoin_base).sum()
    eau_intelligente = (arrosage_intelligent.astype(int) * besoin_base).sum()
    economie_pct = 100 * (1 - eau_intelligente / eau_naive) if eau_naive > 0 else 0

    economie_path = os.path.join(REPORTS_DIR, "economie_eau.txt")
    with open(economie_path, "w", encoding="utf-8") as f:
        f.write("ÉCONOMIE D'EAU — Effet de la météo réelle sur la décision d'arrosage\n")
        f.write("=" * 65 + "\n\n")
        f.write(f"Sur {len(df)} situations simulées avec un sol sec (< 30% d'humidité) :\n\n")
        f.write(f"  Règle naïve (arrose dès que le sol est sec, ignore la météo)\n")
        f.write(f"    -> {arrosage_naif.sum()} arrosages déclenchés, {eau_naive:.0f} L/m² au total\n\n")
        f.write(f"  Règle avec météo réelle (annule si pluie prévue >= 5 mm sous 24h)\n")
        f.write(f"    -> {arrosage_intelligent.sum()} arrosages déclenchés, "
                f"{eau_intelligente:.0f} L/m² au total\n\n")
        f.write(f"Économie estimée grâce à la météo : {economie_pct:.1f} %\n")
    print(f"Analyse d'économie d'eau : {economie_path} ({economie_pct:.1f} % d'économie estimée)")

    # ------------------------------------------------------------
    # 9. Importance des variables (baseline RandomForest, interprétable)
    # ------------------------------------------------------------
    # On utilise le RandomForest pour ce graphique (pas le MLP) car son
    # importance des variables est directement lisible, contrairement à un
    # réseau de neurones ("boîte noire" par nature) — c'est ce qui permet à
    # l'app d'expliquer concrètement les décisions au lieu de rester vague.
    importances = rf.feature_importances_
    noms = colonnes_features()
    ordre = np.argsort(importances)[::-1]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh([noms[i] for i in ordre][::-1], [importances[i] for i in ordre][::-1], color="#2f7d4f")
    ax.set_xlabel("Importance (RandomForest)")
    ax.set_title("Quelles variables influencent le plus la décision ?")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "importance_variables.png"), dpi=150)
    plt.close(fig)
    print(f"Importance des variables : {os.path.join(REPORTS_DIR, 'importance_variables.png')}")

    print("\nRésumé :")
    print(f"  MLP (réseau de neurones) -> accuracy = {metriques_mlp['accuracy']:.3f}")
    print(f"  RandomForest              -> accuracy = {metriques_rf['accuracy']:.3f}")
    print(f"  Économie d'eau estimée    -> {economie_pct:.1f} %")


if __name__ == "__main__":
    entrainer()
