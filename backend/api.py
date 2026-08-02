"""
api.py
======

API FastAPI qui expose la logique d'irrigation (src/) au frontend statique
(frontend/), et sert directement ce frontend — une seule commande à lancer :

    python backend/api.py

puis ouvrir http://localhost:8000
"""

import os
import sys
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ------------------------------------------------------------------
# Configuration des chemins d'import système
# ------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

SRC_DIR = os.path.join(ROOT_DIR, "src")
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Ajouter ROOT_DIR, src et data au PATH système
for path in [ROOT_DIR, SRC_DIR, DATA_DIR]:
    if path not in sys.path:
        sys.path.append(path)

# Imports sécurisés
from src.dataset import CATEGORIES_CULTURE, CATEGORIES_SOL, entree_unique
from data.generate_dataset import BESOIN_BASE_CULTURE
from src.meteo import obtenir_meteo
from src.predict import _charger_artefacts, predire_arrosage
from src.reservoir import (
    EtatReservoir,
    consommer,
    recharger_manuellement,
    recharger_pluie,
)

REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

# Les 4 zones de la ferme simulée
ZONES = [
    {
        "nom": "Zone A",
        "sol": "Sableux",
        "culture": "Maraîchage",
        "humidite_defaut": 22,
    },
    {
        "nom": "Zone B",
        "sol": "Limoneux",
        "culture": "Céréales",
        "humidite_defaut": 55,
    },
    {
        "nom": "Zone C",
        "sol": "Argileux",
        "culture": "Arboriculture",
        "humidite_defaut": 68,
    },
    {
        "nom": "Zone D",
        "sol": "Sableux",
        "culture": "Céréales",
        "humidite_defaut": 15,
    },
]

reservoir_global = EtatReservoir()

app = FastAPI(title="IrrigAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Schémas des requêtes
# ------------------------------------------------------------------
class PredictionRequest(BaseModel):
    humidite_sol: float
    temperature_air: float
    humidite_air: float
    pluie_prevue_mm: float
    type_sol: str
    type_culture: str


class ZonesRequest(BaseModel):
    humidites_sol: List[float]
    temperature_air: float = 25.0
    humidite_air: float = 50.0
    pluie_prevue_mm: float = 0.0


class RechargeRequest(BaseModel):
    litres: float


class ScenarioRequest(BaseModel):
    humidite_sol: float
    humidite_air: float
    pluie_prevue_mm: float
    type_sol: str
    type_culture: str
    temp_base: float
    temp_hypothese: float


# ------------------------------------------------------------------
# Routes API
# ------------------------------------------------------------------
@app.get("/api/config")
def config():
    return {
        "sols": CATEGORIES_SOL,
        "cultures": CATEGORIES_CULTURE,
        "zones": ZONES,
    }


@app.post("/api/predire")
def predire(req: PredictionRequest):
    message = predire_arrosage(
        req.humidite_sol,
        req.temperature_air,
        req.humidite_air,
        req.pluie_prevue_mm,
        req.type_sol,
        req.type_culture,
    )
    return {"message": message}


@app.get("/api/meteo")
def meteo(ville: str = "Pointe-Noire"):
    data = obtenir_meteo(ville)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Ville introuvable ou météo indisponible.",
        )
    return data


@app.post("/api/zones/analyser")
def analyser_zones(req: ZonesRequest):
    global reservoir_global

    if req.pluie_prevue_mm > 0:
        reservoir_global, msg_pluie = recharger_pluie(
            reservoir_global, req.pluie_prevue_mm
        )
    else:
        msg_pluie = "☀️ Pas de pluie aujourd'hui : aucune recharge du réservoir."

    model, scaler = _charger_artefacts()
    resultats = []
    total_litres = 0.0

    for zone, humidite_sol in zip(ZONES, req.humidites_sol):
        X = entree_unique(
            humidite_sol,
            req.temperature_air,
            req.humidite_air,
            req.pluie_prevue_mm,
            zone["sol"],
            zone["culture"],
        )
        proba = float(model.predict_proba(scaler.transform(X))[0, 1])

        if proba > 0.6:
            statut, litres = "arrosage", BESOIN_BASE_CULTURE[zone["culture"]]
            reservoir_global, _ = consommer(reservoir_global, litres)
            total_litres += litres
        elif proba > 0.4:
            statut, litres = "surveiller", 0.0
        else:
            statut, litres = "stable", 0.0

        resultats.append(
            {
                "nom": zone["nom"],
                "sol": zone["sol"],
                "culture": zone["culture"],
                "humidite_sol": humidite_sol,
                "statut": statut,
                "confiance": proba,
                "litres_utilises": litres,
            }
        )

    return {
        "zones": resultats,
        "message_pluie": msg_pluie,
        "reservoir": {
            "niveau_l": reservoir_global.niveau_l,
            "capacite_l": reservoir_global.capacite_l,
            "niveau_pct": reservoir_global.niveau_pct,
            "en_alerte": reservoir_global.en_alerte,
        },
        "total_litres_jour": total_litres,
    }


@app.get("/api/reservoir")
def etat_reservoir():
    return {
        "niveau_l": reservoir_global.niveau_l,
        "capacite_l": reservoir_global.capacite_l,
        "niveau_pct": reservoir_global.niveau_pct,
        "en_alerte": reservoir_global.en_alerte,
    }


@app.post("/api/reservoir/recharger")
def recharger(req: RechargeRequest):
    global reservoir_global
    reservoir_global = recharger_manuellement(reservoir_global, req.litres)
    return {
        "niveau_l": reservoir_global.niveau_l,
        "niveau_pct": reservoir_global.niveau_pct,
    }


@app.get("/api/economie-eau")
def economie_eau():
    chemin = os.path.join(REPORTS_DIR, "economie_eau.txt")
    if not os.path.exists(chemin):
        return {
            "texte": "Lance `python src/train.py` pour générer cette analyse."
        }
    with open(chemin, encoding="utf-8") as f:
        return {"texte": f.read()}


@app.get("/api/metriques")
def metriques():
    chemin = os.path.join(REPORTS_DIR, "metriques.txt")
    if not os.path.exists(chemin):
        return {
            "texte": "Lance `python src/train.py` pour générer cette analyse."
        }
    with open(chemin, encoding="utf-8") as f:
        return {"texte": f.read()}


@app.get("/api/importance-variables")
def importance_variables():
    chemin = os.path.join(REPORTS_DIR, "importance_variables.png")
    if not os.path.exists(chemin):
        raise HTTPException(
            status_code=404,
            detail="Graphique non généré. Lance src/train.py.",
        )
    return FileResponse(chemin, media_type="image/png")


@app.post("/api/comparer-scenarios")
def comparer_scenarios(req: ScenarioRequest):
    base = predire_arrosage(
        req.humidite_sol,
        req.temp_base,
        req.humidite_air,
        req.pluie_prevue_mm,
        req.type_sol,
        req.type_culture,
    )
    hypothese = predire_arrosage(
        req.humidite_sol,
        req.temp_hypothese,
        req.humidite_air,
        req.pluie_prevue_mm,
        req.type_sol,
        req.type_culture,
    )
    return {"scenario_actuel": base, "scenario_hypothese": hypothese}


# Intégration du Frontend statique
if os.path.exists(FRONTEND_DIR):
    app.mount(
        "/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend"
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)