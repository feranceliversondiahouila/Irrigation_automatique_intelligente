import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import time
import random

# 1. Chargement et entraînement rapide du modèle sur les données existantes
print("Chargement des données et entraînement du modèle pour la simulation...")
df = pd.read_csv("donnees_irrigation.csv")

X = df[['humidite', 'temperature']].values
y = df['arrosage'].values.reshape(-1, 1)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
y_tensor = torch.tensor(y, dtype=torch.float32)

class DeepIrrigationModel(nn.Module):
    def __init__(self):
        super(DeepIrrigationModel, self).__init__()
        self.deep_network = nn.Sequential(
            nn.Linear(2, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.deep_network(x)

model = DeepIrrigationModel()
critere = nn.BCELoss()
optimiseur = torch.optim.Adam(model.parameters(), lr=0.01)

# Entraînement rapide avec affichage de la perte en direct
model.train()
print("Début de l'apprentissage...")
for epoch in range(300):
    optimiseur.zero_grad()
    predictions = model(X_tensor)
    perte = critere(predictions, y_tensor)
    perte.backward()
    optimiseur.step()
    
    # Afficher la progression et la baisse de l'erreur tous les 50 tours
    if (epoch + 1) % 50 == 0:
        print(f"Époque [{epoch+1}/300] - Erreur (Loss) : {perte.item():.4f}")

print("Entraînement terminé avec succès !")

# Évaluation du modèle sur les données d'entraînement
model.eval()
with torch.no_grad():
    sorties_test = model(X_tensor)
    # Conversion des probabilités (> 0.5) en prédictions binaires (0 ou 1)
    predictions_binaires = (sorties_test > 0.5).float()
    
    # Calcul du nombre de bonnes prédictions
    correctes = (predictions_binaires == y_tensor).sum().item()
    total = y_tensor.size(0)
    precision = (correctes / total) * 100

print(f"\n📊 --- RAPPORT D'AMÉLIORATION ---")
print(f"Précision du modèle sur les données : {precision:.2f}% ({correctes}/{total} bonnes prédictions)")
# 2. Boucle de simulation du capteur virtuel
try:
    while True:
        # Simulation de mesures de capteurs aléatoires (ou vous pouvez les saisir)
        humidite_simulee = round(random.uniform(10.0, 95.0), 1)
        temperature_simulee = round(random.uniform(18.0, 40.0), 1)
        
        # Préparation des données pour le modèle
        entree_utilisateur = np.array([[humidite_simulee, temperature_simulee]])
        entree_scaled = scaler.transform(entree_utilisateur)
        entrees_tensor = torch.tensor(entree_scaled, dtype=torch.float32)
        
        with torch.no_grad():
            prediction = model(entrees_tensor).item()
        
        # Affichage des résultats du capteur virtuel
        print(f"📡 [Capteur Virtuel] Humidité : {humidite_simulee}% | Température : {temperature_simulee}°C")
        
        if prediction > 0.5:
            print(f"🔴 Décision IA : Sol sec (Confiance : {prediction:.2f}) -> Pompe activée 💧\n")
        else:
            print(f"🟢 Décision IA : Sol correct (Confiance : {1 - prediction:.2f}) -> Pompe éteinte\n")
        
        # Pause de 5 secondes avant la prochaine lecture simulée
        time.sleep(5)

except KeyboardInterrupt:
    print("\nSimulation arrêtée par l'utilisateur.")