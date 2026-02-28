"""
store.py — Couche de persistance légère (JSON)

Structure du store:
  - planning              : planning de la semaine courante (mutable)
  - absences              : toutes les absences enregistrées
  - employes_soldes       : soldes de congés par employé (séparé de data.py pour mutabilité)
  - planning_reference    : planning-type de la semaine (pour les récurrences)
  - notifications         : messages destinés aux employés
  - historique_actions    : journal de toutes les actions effectuées
"""

import json
import os
from datetime import datetime
from copy import deepcopy
from data import PLANNING_SEMAINE, ABSENCES, EMPLOYES

STORE_FILE = "pharmassist_store.json"


# ─────────────────────────────────────────────
# INITIALISATION
# ─────────────────────────────────────────────

def _default_store() -> dict:
    """
    Construit l'état initial à partir de data.py.
    employes_soldes est initialisé depuis EMPLOYES mais vivra
    indépendamment ensuite — c'est ce qui permet la déduction des congés.
    """
    return {
        "planning": deepcopy(PLANNING_SEMAINE),
        "absences": deepcopy(ABSENCES),
        # Soldes de congés mutables — clé = nom employé, valeur = jours restants
        "employes_soldes": {
            e["nom"]: e["jours_conge_restants"] for e in EMPLOYES
        },
        # Planning de référence pour les semaines récurrentes (vide au départ)
        "planning_reference": {},
        # Notifications pour les employés
        "notifications": [],
        "historique_actions": []
    }


def load_store() -> dict:
    if os.path.exists(STORE_FILE):
        store = {}
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            store = json.load(f)
        # Migration : ajouter les clés manquantes si le fichier est ancien
        defaults = _default_store()
        for key in defaults:
            if key not in store:
                store[key] = defaults[key]
        return store
    return _default_store()


def save_store(store: dict):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def reset_store():
    """Remet le store à l'état initial (données de data.py)."""
    store = _default_store()
    save_store(store)
    return store


# ─────────────────────────────────────────────
# SOLDES DE CONGÉS
# ─────────────────────────────────────────────

def get_solde_conges(nom: str) -> int:
    """Retourne le solde de congés actuel d'un employé depuis le store."""
    store = load_store()
    return store["employes_soldes"].get(nom, 0)


def deduire_conge(store: dict, nom: str, jours: int = 1) -> bool:
    """
    Déduit `jours` du solde de congés de l'employé dans le store.
    Retourne True si la déduction a réussi, False si solde insuffisant.
    """
    solde_actuel = store["employes_soldes"].get(nom, 0)
    if solde_actuel < jours:
        return False
    store["employes_soldes"][nom] = solde_actuel - jours
    return True


def restituer_conge(store: dict, nom: str, jours: int = 1):
    """Restitue `jours` au solde de congés (utilisé lors d'un rejet ou annulation)."""
    store["employes_soldes"][nom] = store["employes_soldes"].get(nom, 0) + jours


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

def add_notification(store: dict, destinataire: str, message: str, type_notif: str = "info"):
    """
    Ajoute une notification pour un employé ou pour tous ("TOUS").
    type_notif: "info" | "warning" | "success" | "urgent"
    """
    store["notifications"].append({
        "id": len(store["notifications"]) + 1,
        "destinataire": destinataire,   # nom employé ou "TOUS"
        "message": message,
        "type": type_notif,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "lu": False
    })


def get_notifications(nom: str) -> list:
    """Retourne les notifications d'un employé (les siennes + celles pour TOUS)."""
    store = load_store()
    return [
        n for n in store["notifications"]
        if n["destinataire"] == nom or n["destinataire"] == "TOUS"
    ]


def mark_notifications_read(nom: str):
    """Marque toutes les notifications d'un employé comme lues."""
    store = load_store()
    for n in store["notifications"]:
        if n["destinataire"] == nom or n["destinataire"] == "TOUS":
            n["lu"] = True
    save_store(store)


# ─────────────────────────────────────────────
# JOURNAL D'ACTIONS
# ─────────────────────────────────────────────

def log_action(store: dict, action: str, details: dict):
    store["historique_actions"].append({
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "action": action,
        "details": details
    })
    save_store(store)