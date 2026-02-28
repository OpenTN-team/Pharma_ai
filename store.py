"""
store.py — Couche de persistance légère (JSON)
Remplace les dicts statiques de data.py par un état mutable sauvegardé sur disque.
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
    return {
        "planning": deepcopy(PLANNING_SEMAINE),
        "absences": deepcopy(ABSENCES),
        "historique_actions": []
    }


def load_store() -> dict:
    if os.path.exists(STORE_FILE):
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
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
# JOURNAL D'ACTIONS
# ─────────────────────────────────────────────

def log_action(store: dict, action: str, details: dict):
    store["historique_actions"].append({
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "action": action,
        "details": details
    })
    save_store(store)