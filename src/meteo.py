"""
meteo.py
========

Récupère de VRAIES données météo (API Open-Meteo, gratuite, sans clé) pour
enrichir les prédictions avec la pluie réellement prévue, plutôt que de se
fier uniquement à des données simulées.

Deux appels à l'API :
1. Géocodage : convertit un nom de ville en coordonnées GPS
2. Prévisions : température/humidité actuelles + cumul de pluie sur 3 jours

En cas d'échec réseau (pas de connexion, ville introuvable...), les
fonctions retournent None plutôt que de faire planter l'application ;
l'interface peut alors basculer sur une saisie manuelle.
"""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

TIMEOUT = 6  # secondes : on ne bloque pas l'app si Open-Meteo est lent/injoignable


def geocoder_ville(nom_ville: str):
    """Convertit un nom de ville en coordonnées GPS.
    Retourne (latitude, longitude, nom_affiche) ou None si introuvable."""
    try:
        resp = requests.get(
            GEOCODING_URL,
            params={"name": nom_ville, "count": 1, "language": "fr", "format": "json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        resultats = resp.json().get("results")
        if not resultats:
            return None
        r = resultats[0]
        nom_affiche = f"{r['name']}, {r.get('country', '')}".strip(", ")
        return r["latitude"], r["longitude"], nom_affiche
    except (requests.RequestException, KeyError, ValueError):
        return None


def obtenir_meteo(nom_ville: str):
    """Retourne un dict avec la météo actuelle et la pluie prévue à 72h,
    ou None si la ville est introuvable / en cas d'erreur réseau.

    Clés retournées :
        ville, temperature_actuelle, humidite_air_actuelle,
        pluie_aujourdhui_mm, pluie_3_jours (liste de tuples date/mm),
        pluie_totale_72h_mm
    """
    localisation = geocoder_ville(nom_ville)
    if localisation is None:
        return None
    lat, lon, nom_affiche = localisation

    try:
        resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m",
                "daily": "precipitation_sum",
                "forecast_days": 3,
                "timezone": "auto",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        pluie_3j = data["daily"]["precipitation_sum"]
        dates = data["daily"]["time"]

        return {
            "ville": nom_affiche,
            "temperature_actuelle": data["current"]["temperature_2m"],
            "humidite_air_actuelle": data["current"]["relative_humidity_2m"],
            "pluie_aujourdhui_mm": pluie_3j[0],
            "pluie_3_jours": list(zip(dates, pluie_3j)),
            "pluie_totale_72h_mm": round(sum(pluie_3j), 1),
        }
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None
