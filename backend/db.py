"""
db.py
=====

Base de données SQLite locale (fichier unique, aucun serveur de base de
données à installer). Stocke :

- users      : comptes (superutilisateur ou non). Mots de passe EN CLAIR,
               volontairement (choix explicite pour ce projet pédagogique —
               voir le README pour la mise en garde correspondante).
- zones      : les zones de la ferme, créées/modifiées par le superutilisateur
               (nom, ville, sol, culture, surface, humidité "capteur" saisie
               manuellement, modes automatiques arrosage/traitement).
- reservoirs : 2 lignes fixes ("eau" et "pesticide") avec niveau/capacité.
- journal    : historique des actions automatiques (arrosage, traitement).

Aucun mot de passe n'est requis pour ouvrir le fichier de base de données
lui-même (SQLite classique, pas de chiffrement) — conformément à la demande.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "irrigai.db")

CAPACITE_EAU_DEFAUT_L = 5000.0
NIVEAU_EAU_DEFAUT_L = 3000.0
CAPACITE_PESTICIDE_DEFAUT_L = 200.0
NIVEAU_PESTICIDE_DEFAUT_L = 120.0

ZONES_INITIALES = [
    # nom, ville, sol, culture_specifique, surface_hectares, humidite_sol
    ("Zone A", "Pointe-Noire", "Sableux", "Tomate", 1.5, 22.0),
    ("Zone B", "Pointe-Noire", "Limoneux", "Maïs", 3.0, 55.0),
    ("Zone C", "Pointe-Noire", "Argileux", "Pommier", 2.0, 68.0),
    ("Zone D", "Pointe-Noire", "Sableux", "Blé", 4.0, 15.0),
]


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Crée les tables si elles n'existent pas encore, et sème des données
    de démonstration au tout premier lancement (base vide)."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_superuser INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                ville TEXT NOT NULL,
                region TEXT,
                type_sol TEXT NOT NULL,
                culture_specifique TEXT NOT NULL,
                surface_hectares REAL NOT NULL DEFAULT 1.0,
                humidite_sol REAL NOT NULL DEFAULT 40.0,
                arrosage_auto INTEGER NOT NULL DEFAULT 0,
                traitement_auto INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS reservoirs (
                type TEXT PRIMARY KEY,
                niveau_l REAL NOT NULL,
                capacite_l REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                horodatage TEXT NOT NULL,
                zone_nom TEXT,
                action TEXT,
                details TEXT
            );
        """)

        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users (username, password, is_superuser) VALUES (?, ?, 1)",
                ("admin", "admin"),
            )

        if conn.execute("SELECT COUNT(*) FROM zones").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO zones (nom, ville, type_sol, culture_specifique, "
                "surface_hectares, humidite_sol) VALUES (?, ?, ?, ?, ?, ?)",
                ZONES_INITIALES,
            )

        if conn.execute("SELECT COUNT(*) FROM reservoirs").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO reservoirs (type, niveau_l, capacite_l) VALUES (?, ?, ?)",
                [
                    ("eau", NIVEAU_EAU_DEFAUT_L, CAPACITE_EAU_DEFAUT_L),
                    ("pesticide", NIVEAU_PESTICIDE_DEFAUT_L, CAPACITE_PESTICIDE_DEFAUT_L),
                ],
            )


# ------------------------------------------------------------------
# Utilisateurs
# ------------------------------------------------------------------
def verifier_identifiants(username: str, password: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, is_superuser FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        return dict(row) if row else None


def lister_utilisateurs():
    with get_connection() as conn:
        rows = conn.execute("SELECT id, username, is_superuser FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def creer_utilisateur(username: str, password: str, is_superuser: bool = False):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password, is_superuser) VALUES (?, ?, ?)",
            (username, password, int(is_superuser)),
        )
        return cur.lastrowid


def supprimer_utilisateur(user_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ------------------------------------------------------------------
# Zones
# ------------------------------------------------------------------
def lister_zones():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM zones ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def obtenir_zone(zone_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM zones WHERE id = ?", (zone_id,)).fetchone()
        return dict(row) if row else None


def creer_zone(nom, ville, type_sol, culture_specifique, surface_hectares,
               humidite_sol=40.0, region=None):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO zones (nom, ville, region, type_sol, culture_specifique, "
            "surface_hectares, humidite_sol) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nom, ville, region, type_sol, culture_specifique, surface_hectares, humidite_sol),
        )
        return cur.lastrowid


def modifier_zone(zone_id: int, **champs):
    if not champs:
        return
    colonnes = ", ".join(f"{k} = ?" for k in champs)
    valeurs = list(champs.values()) + [zone_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE zones SET {colonnes} WHERE id = ?", valeurs)


def supprimer_zone(zone_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM zones WHERE id = ?", (zone_id,))


# ------------------------------------------------------------------
# Réservoirs (eau / pesticide)
# ------------------------------------------------------------------
def obtenir_reservoir(type_reservoir: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM reservoirs WHERE type = ?", (type_reservoir,)
        ).fetchone()
        return dict(row) if row else None


def maj_niveau_reservoir(type_reservoir: str, niveau_l: float):
    with get_connection() as conn:
        conn.execute(
            "UPDATE reservoirs SET niveau_l = ? WHERE type = ?",
            (max(0.0, niveau_l), type_reservoir),
        )


# ------------------------------------------------------------------
# Journal des actions automatiques
# ------------------------------------------------------------------
def ajouter_journal(zone_nom: str, action: str, details: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO journal (horodatage, zone_nom, action, details) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), zone_nom, action, details),
        )


def lister_journal(limite: int = 50):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM journal ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
        return [dict(r) for r in rows]
