"""
api.py
======

API FastAPI d'IrrigAI — authentification, gestion des zones et utilisateurs
(superutilisateur), diagnostic complet par zone (météo réelle + ML + santé
de la culture + conseils phytosanitaires), réservoirs eau/pesticide.

Sert aussi le frontend statique (frontend/) : une seule commande à lancer :

    python backend/api.py

puis ouvrir http://localhost:8000
"""

import os
import sys

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "src"))
sys.path.append(os.path.join(ROOT_DIR, "data"))

import db
import auth
from predict import predire_arrosage
from dataset import CATEGORIES_SOL, CATEGORIES_CULTURE, CULTURES_SPECIFIQUES
from meteo import obtenir_meteo, geocoder_ville
from reservoir import EtatReservoir, consommer, recharger_pluie, recharger_manuellement
from decision.decision_engine import diagnostic_complet

REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

db.init_db()

app = FastAPI(title="IrrigAI API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ------------------------------------------------------------------
# Authentification — dépendances FastAPI
# ------------------------------------------------------------------
def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Non authentifié.")
    token = authorization[len("Bearer "):]
    user = auth.obtenir_utilisateur(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée.")
    return user


def require_superuser(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Réservé au superutilisateur.")
    return user


# ------------------------------------------------------------------
# Schémas
# ------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    is_superuser: bool = False


class ZoneCreateRequest(BaseModel):
    nom: str
    ville: str
    type_sol: str
    culture_specifique: str
    surface_hectares: float = 1.0
    humidite_sol: float = 40.0


class ZoneUpdateRequest(BaseModel):
    nom: Optional[str] = None
    ville: Optional[str] = None
    type_sol: Optional[str] = None
    culture_specifique: Optional[str] = None
    surface_hectares: Optional[float] = None
    humidite_sol: Optional[float] = None
    arrosage_auto: Optional[bool] = None
    traitement_auto: Optional[bool] = None


class RechargeRequest(BaseModel):
    litres: float


class PredictionRequest(BaseModel):
    humidite_sol: float
    temperature_air: float
    humidite_air: float
    pluie_prevue_mm: float
    type_sol: str
    type_culture: str


class ScenarioRequest(BaseModel):
    humidite_sol: float
    humidite_air: float
    pluie_prevue_mm: float
    type_sol: str
    type_culture: str
    temp_base: float
    temp_hypothese: float


# ------------------------------------------------------------------
# Authentification
# ------------------------------------------------------------------
@app.post("/api/login")
def login(req: LoginRequest):
    user = db.verifier_identifiants(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")
    token = auth.creer_session(user)
    return {"token": token, **user}


@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        auth.detruire_session(authorization[len("Bearer "):])
    return {"ok": True}


@app.get("/api/whoami")
def whoami(user: dict = Depends(get_current_user)):
    return user


# ------------------------------------------------------------------
# Configuration (listes pour les formulaires)
# ------------------------------------------------------------------
@app.get("/api/config")
def config(user: dict = Depends(get_current_user)):
    return {
        "sols": CATEGORIES_SOL,
        "cultures_specifiques": list(CULTURES_SPECIFIQUES.keys()),
        "categories_culture": CATEGORIES_CULTURE,
    }


# ------------------------------------------------------------------
# Zones
# ------------------------------------------------------------------
@app.get("/api/zones")
def get_zones(user: dict = Depends(get_current_user)):
    return db.lister_zones()


@app.post("/api/zones")
def creer_zone(req: ZoneCreateRequest, user: dict = Depends(require_superuser)):
    region = None
    geo = geocoder_ville(req.ville)
    if geo:
        region = geo[3]
    zone_id = db.creer_zone(req.nom, req.ville, req.type_sol, req.culture_specifique,
                             req.surface_hectares, req.humidite_sol, region)
    return db.obtenir_zone(zone_id)


@app.put("/api/zones/{zone_id}")
def modifier_zone(zone_id: int, req: ZoneUpdateRequest, user: dict = Depends(require_superuser)):
    if db.obtenir_zone(zone_id) is None:
        raise HTTPException(status_code=404, detail="Zone introuvable.")
    champs = {k: (int(v) if isinstance(v, bool) else v) for k, v in req.dict().items() if v is not None}
    db.modifier_zone(zone_id, **champs)
    return db.obtenir_zone(zone_id)


@app.delete("/api/zones/{zone_id}")
def supprimer_zone(zone_id: int, user: dict = Depends(require_superuser)):
    if db.obtenir_zone(zone_id) is None:
        raise HTTPException(status_code=404, detail="Zone introuvable.")
    db.supprimer_zone(zone_id)
    return {"ok": True}


@app.get("/api/zones/{zone_id}/diagnostic")
def obtenir_diagnostic(zone_id: int, user: dict = Depends(get_current_user)):
    """Diagnostic en LECTURE SEULE : ne modifie ni réservoir ni base de
    données. Pour déclencher les actions automatiques, voir /cycle-auto."""
    zone = db.obtenir_zone(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone introuvable.")
    resultat = diagnostic_complet(zone)
    resultat["reservoirs"] = {"eau": db.obtenir_reservoir("eau"), "pesticide": db.obtenir_reservoir("pesticide")}
    return resultat


@app.post("/api/zones/{zone_id}/cycle-auto")
def lancer_cycle_auto(zone_id: int, user: dict = Depends(get_current_user)):
    """Exécute un cycle de vérification complet pour la zone : calcule le
    diagnostic, puis DÉCLENCHE réellement l'arrosage et/ou le traitement
    phytosanitaire si les modes automatiques de la zone sont activés
    (consomme les réservoirs, journalise l'action)."""
    zone = db.obtenir_zone(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone introuvable.")

    resultat = diagnostic_complet(zone)
    if "erreur" in resultat:
        return resultat

    # Recharge du réservoir d'eau avec la pluie du jour (indépendant du mode auto)
    pluie = resultat["meteo_temps_reel"]["pluie_aujourdhui_mm"]
    if pluie > 0:
        r = db.obtenir_reservoir("eau")
        etat = EtatReservoir(capacite_l=r["capacite_l"], niveau_l=r["niveau_l"])
        etat, msg_pluie = recharger_pluie(etat, pluie)
        db.maj_niveau_reservoir("eau", etat.niveau_l)
        resultat["recharge_pluie"] = msg_pluie

    # Arrosage automatique
    if zone["arrosage_auto"] and resultat["decision_arrosage"]["action"] == "ARROSER":
        volume = resultat["decision_arrosage"]["volume_litres_recommande"]
        r = db.obtenir_reservoir("eau")
        etat = EtatReservoir(capacite_l=r["capacite_l"], niveau_l=r["niveau_l"])
        etat, msg = consommer(etat, volume)
        db.maj_niveau_reservoir("eau", etat.niveau_l)
        db.ajouter_journal(zone["nom"], "arrosage_auto", msg)
        resultat["action_automatique_eau"] = msg

    # Traitement phytosanitaire automatique
    if zone["traitement_auto"] and resultat["traitement_recommande"]["necessaire"]:
        volume_pesticide = round(2.0 * zone.get("surface_hectares", 1.0), 1)  # ex : 2 L/ha
        r = db.obtenir_reservoir("pesticide")
        etat = EtatReservoir(capacite_l=r["capacite_l"], niveau_l=r["niveau_l"])
        etat, msg = consommer(etat, volume_pesticide)
        db.maj_niveau_reservoir("pesticide", etat.niveau_l)
        db.ajouter_journal(zone["nom"], "traitement_auto", msg)
        resultat["action_automatique_pesticide"] = msg

    resultat["reservoirs"] = {"eau": db.obtenir_reservoir("eau"), "pesticide": db.obtenir_reservoir("pesticide")}
    return resultat


# ------------------------------------------------------------------
# Utilisateurs (superutilisateur uniquement)
# ------------------------------------------------------------------
@app.get("/api/users")
def get_users(user: dict = Depends(require_superuser)):
    return db.lister_utilisateurs()


@app.post("/api/users")
def creer_utilisateur(req: UserCreateRequest, user: dict = Depends(require_superuser)):
    try:
        user_id = db.creer_utilisateur(req.username, req.password, req.is_superuser)
    except Exception:
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur existe déjà.")
    return {"id": user_id, "username": req.username, "is_superuser": req.is_superuser}


@app.delete("/api/users/{user_id}")
def supprimer_utilisateur(user_id: int, user: dict = Depends(require_superuser)):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Impossible de supprimer son propre compte.")
    db.supprimer_utilisateur(user_id)
    return {"ok": True}


# ------------------------------------------------------------------
# Réservoirs
# ------------------------------------------------------------------
@app.get("/api/reservoirs")
def get_reservoirs(user: dict = Depends(get_current_user)):
    return {"eau": db.obtenir_reservoir("eau"), "pesticide": db.obtenir_reservoir("pesticide")}


@app.post("/api/reservoirs/{type_reservoir}/recharger")
def recharger_reservoir(type_reservoir: str, req: RechargeRequest, user: dict = Depends(require_superuser)):
    if type_reservoir not in ("eau", "pesticide"):
        raise HTTPException(status_code=400, detail="Type de réservoir invalide (eau ou pesticide).")
    r = db.obtenir_reservoir(type_reservoir)
    etat = EtatReservoir(capacite_l=r["capacite_l"], niveau_l=r["niveau_l"])
    etat = recharger_manuellement(etat, req.litres)
    db.maj_niveau_reservoir(type_reservoir, etat.niveau_l)
    return db.obtenir_reservoir(type_reservoir)


# ------------------------------------------------------------------
# Journal des actions automatiques
# ------------------------------------------------------------------
@app.get("/api/journal")
def get_journal(user: dict = Depends(get_current_user)):
    return db.lister_journal()


# ------------------------------------------------------------------
# Rapports (générés par src/train.py)
# ------------------------------------------------------------------
@app.get("/api/economie-eau")
def economie_eau(user: dict = Depends(get_current_user)):
    chemin = os.path.join(REPORTS_DIR, "economie_eau.txt")
    if not os.path.exists(chemin):
        return {"texte": "Lance `python src/train.py` pour générer cette analyse."}
    with open(chemin, encoding="utf-8") as f:
        return {"texte": f.read()}


@app.get("/api/metriques")
def metriques(user: dict = Depends(get_current_user)):
    chemin = os.path.join(REPORTS_DIR, "metriques.txt")
    if not os.path.exists(chemin):
        return {"texte": "Lance `python src/train.py` pour générer cette analyse."}
    with open(chemin, encoding="utf-8") as f:
        return {"texte": f.read()}


@app.get("/api/importance-variables")
def importance_variables():
    chemin = os.path.join(REPORTS_DIR, "importance_variables.png")
    if not os.path.exists(chemin):
        raise HTTPException(status_code=404, detail="Graphique non généré. Lance src/train.py.")
    return FileResponse(chemin, media_type="image/png")


# ------------------------------------------------------------------
# Simulateur ponctuel (onglet Analyse)
# ------------------------------------------------------------------
@app.post("/api/predire")
def predire(req: PredictionRequest, user: dict = Depends(get_current_user)):
    message = predire_arrosage(req.humidite_sol, req.temperature_air, req.humidite_air,
                                req.pluie_prevue_mm, req.type_sol, req.type_culture)
    return {"message": message}


@app.post("/api/comparer-scenarios")
def comparer_scenarios(req: ScenarioRequest, user: dict = Depends(get_current_user)):
    base = predire_arrosage(req.humidite_sol, req.temp_base, req.humidite_air,
                             req.pluie_prevue_mm, req.type_sol, req.type_culture)
    hypothese = predire_arrosage(req.humidite_sol, req.temp_hypothese, req.humidite_air,
                                  req.pluie_prevue_mm, req.type_sol, req.type_culture)
    return {"scenario_actuel": base, "scenario_hypothese": hypothese}


@app.get("/api/meteo")
def meteo(ville: str, user: dict = Depends(get_current_user)):
    data = obtenir_meteo(ville)
    if data is None:
        raise HTTPException(status_code=404, detail="Ville introuvable ou météo indisponible.")
    return data


# Sert le frontend statique (index.html, css, js) directement à la racine "/"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # La plupart des hébergeurs (Render, Railway, Fly.io...) imposent leur
    # propre port via la variable d'environnement PORT. En local, on garde
    # 8000 par défaut.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
