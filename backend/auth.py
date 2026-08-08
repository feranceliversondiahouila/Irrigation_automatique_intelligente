"""
auth.py
=======

Gestion de session très simple : un jeton aléatoire par connexion, conservé
en mémoire côté serveur (pas de JWT, pas de cookies signés — volontairement
minimal pour rester lisible et facile à expliquer).

Le jeton est envoyé par le frontend dans l'en-tête HTTP :
    Authorization: Bearer <jeton>
"""

import secrets

_sessions = {}  # token -> {"id": int, "username": str, "is_superuser": bool}


def creer_session(utilisateur: dict) -> str:
    token = secrets.token_hex(20)
    _sessions[token] = utilisateur
    return token


def obtenir_utilisateur(token: str):
    return _sessions.get(token)


def detruire_session(token: str):
    _sessions.pop(token, None)
