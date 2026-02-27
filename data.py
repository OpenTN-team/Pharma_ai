from datetime import datetime, timedelta
import json

# ============================================================
# DONNÉES FICTIVES — Pharmacie des Lilas (Lyon)
# ============================================================

PHARMACIE = {
    "nom": "Pharmacie des Lilas",
    "ville": "Lyon",
    "horaires": "Lundi-Vendredi 8h-20h, Samedi 9h-18h"
}

EMPLOYES = [
    {
        "id": 1,
        "nom": "Sophie Martin",
        "role": "Pharmacienne diplômée (PDE)",
        "qualifie": True,
        "heures_semaine": 35,
        "jours_conge_restants": 12,
        "disponibilites": ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
    },
    {
        "id": 2,
        "nom": "Thomas Dupont",
        "role": "Pharmacien diplômé (PDE)",
        "qualifie": True,
        "heures_semaine": 35,
        "jours_conge_restants": 8,
        "disponibilites": ["lundi", "mardi", "jeudi", "vendredi", "samedi"]
    },
    {
        "id": 3,
        "nom": "Marie Leroy",
        "role": "Préparatrice en pharmacie",
        "qualifie": False,
        "heures_semaine": 35,
        "jours_conge_restants": 15,
        "disponibilites": ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
    },
    {
        "id": 4,
        "nom": "Karim Benali",
        "role": "Préparateur en pharmacie",
        "qualifie": False,
        "heures_semaine": 28,
        "jours_conge_restants": 10,
        "disponibilites": ["mardi", "mercredi", "jeudi", "vendredi", "samedi"]
    },
    {
        "id": 5,
        "nom": "Julie Bernard",
        "role": "Préparatrice en pharmacie",
        "qualifie": False,
        "heures_semaine": 35,
        "jours_conge_restants": 5,
        "disponibilites": ["lundi", "mercredi", "jeudi", "vendredi", "samedi"]
    },
    {
        "id": 6,
        "nom": "Pierre Moreau",
        "role": "Pharmacien diplômé (PDE)",
        "qualifie": True,
        "heures_semaine": 35,
        "jours_conge_restants": 20,
        "disponibilites": ["lundi", "mardi", "mercredi", "samedi"]
    }
]

# Planning de la semaine en cours (3-8 mars 2025)
PLANNING_SEMAINE = {
    "lundi": {
        "matin": ["Sophie Martin", "Marie Leroy", "Julie Bernard"],
        "apres_midi": ["Sophie Martin", "Karim Benali", "Julie Bernard"]
    },
    "mardi": {
        "matin": ["Thomas Dupont", "Marie Leroy", "Karim Benali"],
        "apres_midi": ["Thomas Dupont", "Marie Leroy", "Karim Benali"]
    },
    "mercredi": {
        "matin": ["Sophie Martin", "Marie Leroy", "Julie Bernard"],
        "apres_midi": ["Pierre Moreau", "Julie Bernard"]
    },
    "jeudi": {
        "matin": ["Thomas Dupont", "Marie Leroy", "Karim Benali"],
        "apres_midi": ["Thomas Dupont", "Julie Bernard", "Karim Benali"]
    },
    "vendredi": {
        "matin": ["Sophie Martin", "Marie Leroy", "Julie Bernard"],
        "apres_midi": ["Thomas Dupont", "Marie Leroy", "Karim Benali"]
    },
    "samedi": {
        "matin": ["Pierre Moreau", "Karim Benali", "Julie Bernard"],
        "apres_midi": ["Thomas Dupont", "Julie Bernard"]
    }
}

# Absences enregistrées
ABSENCES = [
    {
        "employe": "Marie Leroy",
        "date": "2025-03-05",
        "type": "Maladie",
        "statut": "Validée",
        "remplacant": "Julie Bernard"
    },
    {
        "employe": "Karim Benali",
        "date": "2025-03-10",
        "type": "Congé payé",
        "statut": "En attente",
        "remplacant": None
    }
]

# Alertes et périodes de surcharge
ALERTES = [
    {
        "type": "Surcharge prévue",
        "message": "Début du mois de mars : forte affluence prévue (remboursements Sécurité Sociale)",
        "niveau": "orange",
        "semaine": "S1 Mars"
    },
    {
        "type": "Période grippale",
        "message": "Pic grippal en cours — prévoir stock et personnel renforcé",
        "niveau": "rouge",
        "semaine": "S1-S2 Mars"
    },
    {
        "type": "Absence non couverte",
        "message": "Karim Benali absent le 10 mars — remplacement non assigné",
        "niveau": "rouge",
        "semaine": "S2 Mars"
    }
]

# Métriques RH
METRIQUES = {
    "taux_couverture": 94,
    "heures_planifiees_semaine": 187,
    "heures_legales_semaine": 210,
    "absences_ce_mois": 2,
    "alertes_actives": 3
}

def get_contexte_complet():
    """Retourne toutes les données sous forme de texte pour l'agent IA"""
    return f"""
    PHARMACIE: {PHARMACIE['nom']} — {PHARMACIE['ville']}
    HORAIRES: {PHARMACIE['horaires']}
    
    ÉQUIPE ({len(EMPLOYES)} employés):
    {json.dumps(EMPLOYES, ensure_ascii=False, indent=2)}
    
    PLANNING SEMAINE EN COURS:
    {json.dumps(PLANNING_SEMAINE, ensure_ascii=False, indent=2)}
    
    ABSENCES:
    {json.dumps(ABSENCES, ensure_ascii=False, indent=2)}
    
    ALERTES ACTIVES:
    {json.dumps(ALERTES, ensure_ascii=False, indent=2)}
    
    MÉTRIQUES:
    {json.dumps(METRIQUES, ensure_ascii=False, indent=2)}
    
    RÈGLES LÉGALES (Convention Collective Pharmacie — IDCC 1996):
    - Durée légale: 35h/semaine, max 10h/jour
    - Un pharmacien diplômé d'État (PDE) OBLIGATOIRE à tout moment d'ouverture
    - Repos hebdomadaire obligatoire (dimanche)
    - Congés payés: 25 jours ouvrés/an minimum
    """