import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

print("Chargement des données dans model.py...")
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
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.deep_network(x)

model = DeepIrrigationModel()
critere = nn.BCELoss()
optimiseur = optim.Adam(model.parameters(), lr=0.005)

print("Entraînement du modèle en cours...")
model.train()
for epoch in range(800):
    optimiseur.zero_grad()
    predictions = model(X_tensor)
    perte = critere(predictions, y_tensor)
    perte.backward()
    optimiseur.step()

print("Modèle prêt !")

# Fonction exportée pour l'interface
def predire_arrosage(humidite_sol, temperature):
    model.eval()
    entree_utilisateur = np.array([[humidite_sol, temperature]])
    entree_scaled = scaler.transform(entree_utilisateur)
    entrees_tensor = torch.tensor(entree_scaled, dtype=torch.float32)
    
    with torch.no_grad():
        prediction = model(entrees_tensor).item()
    
    if prediction > 0.5:
        return f"🔴 Alerte Deep Learning : Arrosage REQUIS (Confiance : {prediction:.2f})"
    else:
        return f"🟢 Deep Learning : Sol stable, pas besoin d'arroser (Confiance : {1 - prediction:.2f})"