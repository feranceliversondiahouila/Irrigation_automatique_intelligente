# 🌱 Irrigation Automatique Intelligente

Système d'aide à la décision qui prédit **s'il faut arroser une parcelle**, à
partir de mesures climatiques et agronomiques (humidité du sol, température,
humidité de l'air, pluie prévue, type de sol, type de culture).

100 % piloté par les données : aucun capteur physique n'est nécessaire pour
faire tourner le projet, tout est simulé de façon réaliste et documentée.

## Pourquoi ce projet est data-driven et pas juste une démo

- Le **dataset** (`data/generate_dataset.py`) est généré à partir de règles
  agronomiques explicites (rétention d'eau par type de sol, besoin en eau par
  culture, effet de la température/humidité/pluie) **+ du bruit aléatoire**,
  pour éviter un jeu de données artificiellement "trop parfait".
- Le modèle est **évalué sur un jeu de test qu'il n'a jamais vu**
  (80 % train / 20 % test), avec accuracy, precision, recall et F1-score —
  pas juste "ça marche sur l'exemple que j'ai montré".
- Une **baseline classique (RandomForest)** est entraînée en parallèle du
  réseau de neurones, pour pouvoir justifier objectivement le choix du
  modèle (comparaison chiffrée, pas une affirmation en l'air).

## Pourquoi scikit-learn plutôt que PyTorch/TensorFlow ?

Le modèle est un **réseau de neurones multicouche (MLP)** via
`sklearn.neural_network.MLPClassifier` — mêmes concepts fondamentaux
(couches cachées, activation ReLU, rétropropagation, optimiseur Adam)
qu'un réseau PyTorch, mais :
- installation légère (aucune dépendance ne dépasse quelques Mo, contre
  ~150 Mo pour PyTorch),
- pas de risque d'échec d'installation sous Windows lié aux chemins de
  fichiers trop longs (problème connu de PyTorch avec le Python du
  Microsoft Store),
- idéal pour partager le projet facilement avec un jury ou des
  collaborateurs sans configuration compliquée.

C'est un choix technique assumé et justifiable à l'oral : la taille du
dataset (2000 lignes, 10 features) ne nécessite de toute façon pas la
puissance d'un framework de Deep Learning industriel.

## Structure du projet

```
IRRIGATION_IA/
├── README.md
├── requirements.txt
├── backend/
│   └── api.py                 # API FastAPI — sert aussi le frontend statique
├── frontend/                  # Interface web (HTML/CSS/JS pur, sans framework)
│   ├── index.html               # Page unique, sections ancrées
│   ├── css/style.css             # Design "liquid glass" + thème clair/sombre
│   └── js/app.js                  # Appels à l'API, interactions
├── simulation_capteur.py      # Simulation d'un flux de capteur en direct
├── data/
│   ├── generate_dataset.py     # Génère le dataset (règles + bruit aléatoire)
│   └── irrigation_dataset.csv   # Dataset généré (2000 lignes, lisible/CSV)
├── src/
│   ├── dataset.py               # Prétraitement partagé (encodage, features)
│   ├── model.py                  # Définition du modèle (MLPClassifier scikit-learn)
│   ├── train.py                   # Entraînement + évaluation + rapports + sauvegarde
│   ├── predict.py                  # Chargement du modèle + prédiction
│   ├── meteo.py                     # Intégration météo réelle (API Open-Meteo, sans clé)
│   └── reservoir.py                  # Gestion du réservoir d'eau (niveau, recharge pluie)
├── models/                    # Modèle entraîné (généré par train.py)
└── reports/                   # Métriques + graphiques + analyses (générés par train.py)
```

## L'interface

Page unique en HTML/CSS/JS pur (aucun framework, aucune dépendance externe
côté client hormis les polices Google Fonts), avec :

- **Design "liquid glass"** : panneaux translucides flous (`backdrop-filter:
  blur()`) flottant sur un fond de dégradés ambiants animés — inspiré des
  interfaces "verre dépoli" façon iOS/macOS récents.
- **Thème clair / sombre**, avec bouton de bascule en haut à droite (choix
  mémorisé dans le navigateur, et détection automatique de la préférence
  système au premier chargement).
- **Navigation par ancre** : barre collante en haut qui saute directement à
  chaque section (Paramètres / Dashboard / Analyse), comme un site portfolio.

Le frontend ne fait strictement que de l'affichage : tout le calcul
(prédiction, météo, réservoir) se fait côté serveur via l'API FastAPI
(`backend/api.py`), interrogée en JavaScript (`fetch`).

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

**1. Générer le dataset** (déjà fait, mais reproductible à volonté) :
```bash
python data/generate_dataset.py --n 2000
```

**2. Entraîner le modèle** et générer le rapport d'évaluation :
```bash
python src/train.py
```
Cela produit :
- `models/irrigation_model.joblib` et `models/scaler.joblib` (réseau de neurones)
- `models/random_forest.joblib` (baseline de comparaison)
- `reports/metriques.txt` (accuracy / precision / recall / F1 des 2 modèles)
- `reports/matrice_confusion.png` et `reports/courbe_apprentissage.png`

**3. Lancer l'application** (backend + frontend en une seule commande) :
```bash
python backend/api.py
```
Puis ouvrir **http://localhost:8000** dans le navigateur.

**4. (Optionnel) Simuler un flux de capteur en direct** pour la démo orale :
```bash
python simulation_capteur.py
```

## Résultats obtenus (jeu de test, 400 échantillons)

| Modèle                          | Accuracy | Precision | Recall | F1-score |
|----------------------------------|----------|-----------|--------|----------|
| Réseau de neurones (MLP)          | ~0.76    | ~0.70     | ~0.78  | ~0.74    |
| RandomForest (baseline)            | ~0.75    | ~0.71     | ~0.74  | ~0.72    |

*(valeurs exactes disponibles dans `reports/metriques.txt` après entraînement ;
elles varient légèrement selon la graine aléatoire du dataset généré.)*

**Économie d'eau** : en comparant une règle naïve (arrose dès que le sol est
sec, sans regarder la météo) à la même règle mais qui annule l'arrosage si
de la pluie est prévue sous 24h, l'analyse sur nos données simulées estime
**~19 % d'eau économisée** rien qu'en intégrant une vraie prévision météo
(voir `reports/economie_eau.txt`, généré par `train.py`).

Les deux modèles obtiennent des scores proches : cela s'explique par le fait
que la relation entre les variables et la cible reste en grande partie
explicable par des règles simples. C'est un résultat honnête à présenter :
il montre une vraie démarche de comparaison plutôt qu'un choix arbitraire du
Deep Learning "parce que ça fait sérieux".

## Limites connues (bon point à mentionner à l'oral)

- Le dataset est **simulé**, pas mesuré sur le terrain : les règles utilisées
  sont plausibles mais simplifiées (pas d'effet du vent, de l'ensoleillement,
  du stade de croissance de la culture, etc.).
- Le modèle prédit un besoin binaire (arroser / ne pas arroser) ; la colonne
  `quantite_eau_litres_m2` du dataset est fournie pour une extension future
  en régression (quantité d'eau à apporter), non exploitée dans le modèle
  actuel.
- La récupération météo (`src/meteo.py`) nécessite une connexion Internet.
  En cas d'échec (pas de réseau, ville introuvable), l'app bascule
  automatiquement sur des valeurs par défaut plutôt que de planter.
- Le réservoir d'eau et les 4 zones sont des simulations pour la démo (pas
  de vrai capteur de niveau) ; la logique de consommation/recharge, elle,
  est réelle et cohérente (litres réellement soustraits/ajoutés).
- L'état du réservoir est conservé **en mémoire côté serveur** (une seule
  ferme simulée) : il revient à son niveau de départ si le serveur redémarre.
  Suffisant pour une démo, mais pas persistant (pas de base de données).
