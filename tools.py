"""
tools.py — Définition et exécution des outils de l'agent PharmAssist

Chaque outil a :
  - Un schéma JSON (pour Groq tool calling)
  - Un handler Python (la logique réelle)

Outils disponibles :
  1. get_planning          — Lire le planning courant
  2. modify_planning       — Ajouter/retirer un employé d'un shift
  3. generate_planning     — Générer un planning valide pour une semaine
  4. create_absence        — Enregistrer une demande d'absence
  5. approve_absence       — Approuver une absence + suggérer remplaçant
  6. reject_absence        — Rejeter une demande d'absence
  7. get_absences          — Lister toutes les absences
  8. run_compliance_check  — Lancer le moteur de règles
"""

import json
from datetime import datetime
from data import EMPLOYES
from store import load_store, save_store, log_action
from Rulesengine import suggest_replacement, run_full_compliance_check


# ═════════════════════════════════════════════
#  SCHÉMAS JSON — déclarés pour Groq
# ═════════════════════════════════════════════

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_planning",
            "description": "Retourne le planning de la semaine en cours. Peut filtrer par jour.",
            "parameters": {
                "type": "object",
                "properties": {
                    "jour": {
                        "type": "string",
                        "description": "Jour optionnel (lundi, mardi, etc.). Si absent, retourne toute la semaine.",
                        "enum": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_planning",
            "description": "Ajoute ou retire un employé d'un shift (matin ou apres_midi) d'un jour donné.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employe": {
                        "type": "string",
                        "description": "Nom complet de l'employé (ex: Sophie Martin)"
                    },
                    "jour": {
                        "type": "string",
                        "description": "Jour de la semaine",
                        "enum": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
                    },
                    "shift": {
                        "type": "string",
                        "description": "Créneau concerné",
                        "enum": ["matin", "apres_midi"]
                    },
                    "action": {
                        "type": "string",
                        "description": "ajouter ou retirer l'employé du shift",
                        "enum": ["ajouter", "retirer"]
                    }
                },
                "required": ["employe", "jour", "shift", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_planning",
            "description": "Génère automatiquement un planning valide pour la semaine en respectant les règles légales (PDE obligatoire, disponibilités, 35h max). Remplace le planning courant après confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "remplacer_existant": {
                        "type": "boolean",
                        "description": "Si true, remplace le planning actuel. Si false, retourne seulement une proposition."
                    }
                },
                "required": ["remplacer_existant"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_absence",
            "description": "Enregistre une nouvelle demande d'absence pour un employé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employe": {
                        "type": "string",
                        "description": "Nom complet de l'employé"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date de l'absence au format YYYY-MM-DD"
                    },
                    "type_absence": {
                        "type": "string",
                        "description": "Type d'absence",
                        "enum": ["Maladie", "Congé payé", "Congé sans solde", "Formation", "Autre"]
                    }
                },
                "required": ["employe", "date", "type_absence"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approve_absence",
            "description": "Approuve une absence en attente et assigne automatiquement le meilleur remplaçant disponible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employe": {
                        "type": "string",
                        "description": "Nom complet de l'employé absent"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date de l'absence au format YYYY-MM-DD"
                    }
                },
                "required": ["employe", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reject_absence",
            "description": "Rejette une demande d'absence en attente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employe": {
                        "type": "string",
                        "description": "Nom complet de l'employé"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date de l'absence au format YYYY-MM-DD"
                    },
                    "motif": {
                        "type": "string",
                        "description": "Raison du refus (optionnel)"
                    }
                },
                "required": ["employe", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_absences",
            "description": "Retourne la liste de toutes les absences enregistrées, avec leur statut.",
            "parameters": {
                "type": "object",
                "properties": {
                    "statut": {
                        "type": "string",
                        "description": "Filtrer par statut (optionnel)",
                        "enum": ["En attente", "Validée", "Refusée"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_compliance_check",
            "description": "Lance le moteur de règles et retourne un rapport complet de conformité IDCC 1996.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# ═════════════════════════════════════════════
#  HANDLERS — logique des outils
# ═════════════════════════════════════════════

def handle_get_planning(jour: str = None) -> dict:
    store = load_store()
    planning = store["planning"]
    if jour:
        return {"jour": jour, "planning": planning.get(jour, {})}
    return {"planning": planning}


def handle_modify_planning(employe: str, jour: str, shift: str, action: str) -> dict:
    # Valider l'employé
    emp_info = next((e for e in EMPLOYES if e["nom"].lower() == employe.lower()), None)
    if not emp_info:
        noms = [e["nom"] for e in EMPLOYES]
        return {"succes": False, "erreur": f"Employé '{employe}' introuvable. Employés disponibles: {noms}"}

    employe_nom = emp_info["nom"]
    store = load_store()
    planning = store["planning"]

    if jour not in planning:
        planning[jour] = {"matin": [], "apres_midi": []}
    if shift not in planning[jour]:
        planning[jour][shift] = []

    equipe = planning[jour][shift]

    if action == "ajouter":
        if employe_nom in equipe:
            return {"succes": False, "erreur": f"{employe_nom} est déjà planifié(e) le {jour} {shift}"}
        # Vérifier disponibilité
        if jour not in emp_info["disponibilites"]:
            return {"succes": False, "erreur": f"{employe_nom} n'est pas disponible le {jour} (disponibilités: {emp_info['disponibilites']})"}
        equipe.append(employe_nom)
        log_action(store, "modify_planning", {"action": "ajouter", "employe": employe_nom, "jour": jour, "shift": shift})
        save_store(store)
        return {"succes": True, "message": f"{employe_nom} ajouté(e) le {jour} {shift}", "equipe_mise_a_jour": equipe}

    elif action == "retirer":
        if employe_nom not in equipe:
            return {"succes": False, "erreur": f"{employe_nom} n'est pas planifié(e) le {jour} {shift}"}
        # Vérifier qu'on ne retire pas le seul PDE
        pde_noms = {e["nom"] for e in EMPLOYES if e["qualifie"]}
        if employe_nom in pde_noms:
            autres_pde = [e for e in equipe if e in pde_noms and e != employe_nom]
            if not autres_pde:
                return {
                    "succes": False,
                    "erreur": f"VIOLATION CRITIQUE: Impossible de retirer {employe_nom} — aucun autre PDE présent le {jour} {shift}. Assignez d'abord un remplaçant PDE."
                }
        equipe.remove(employe_nom)
        log_action(store, "modify_planning", {"action": "retirer", "employe": employe_nom, "jour": jour, "shift": shift})
        save_store(store)
        return {"succes": True, "message": f"{employe_nom} retiré(e) du {jour} {shift}", "equipe_mise_a_jour": equipe}

    return {"succes": False, "erreur": "Action invalide"}


def handle_generate_planning(remplacer_existant: bool) -> dict:
    """
    Génère un planning valide pour la semaine en respectant :
    - Présence d'au moins 1 PDE par shift
    - Disponibilités de chaque employé
    - Max 5 shifts/semaine par employé (≈35h)
    """
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
    pde = [e for e in EMPLOYES if e["qualifie"]]
    preparateurs = [e for e in EMPLOYES if not e["qualifie"]]

    planning_genere = {}
    compteur_shifts = {e["nom"]: 0 for e in EMPLOYES}
    max_shifts = {e["nom"]: (e["heures_semaine"] // 4) for e in EMPLOYES}  # 4h par shift

    for jour in jours:
        planning_genere[jour] = {"matin": [], "apres_midi": []}

        for shift in ["matin", "apres_midi"]:
            # 1. Ajouter un PDE disponible avec le moins de shifts
            pde_dispo = [
                e for e in pde
                if jour in e["disponibilites"]
                and compteur_shifts[e["nom"]] < max_shifts[e["nom"]]
            ]
            if not pde_dispo:
                planning_genere[jour][shift].append("⚠️ AUCUN PDE DISPONIBLE")
                continue

            pde_choisi = min(pde_dispo, key=lambda e: compteur_shifts[e["nom"]])
            planning_genere[jour][shift].append(pde_choisi["nom"])
            compteur_shifts[pde_choisi["nom"]] += 1

            # 2. Ajouter 1-2 préparateurs disponibles
            preps_dispo = [
                e for e in preparateurs
                if jour in e["disponibilites"]
                and compteur_shifts[e["nom"]] < max_shifts[e["nom"]]
                and e["nom"] not in planning_genere[jour][shift]
            ]
            preps_dispo.sort(key=lambda e: compteur_shifts[e["nom"]])

            nb_preps = 2 if jour not in ["mercredi"] else 1
            for prep in preps_dispo[:nb_preps]:
                planning_genere[jour][shift].append(prep["nom"])
                compteur_shifts[prep["nom"]] += 1

    if remplacer_existant:
        store = load_store()
        store["planning"] = planning_genere
        log_action(store, "generate_planning", {
            "remplace": True,
            "shifts_par_employe": compteur_shifts
        })
        save_store(store)
        return {
            "succes": True,
            "message": "Planning généré et sauvegardé avec succès.",
            "planning": planning_genere,
            "shifts_par_employe": compteur_shifts
        }

    return {
        "succes": True,
        "message": "Voici une proposition de planning (non sauvegardée). Confirmez pour l'appliquer.",
        "planning": planning_genere,
        "shifts_par_employe": compteur_shifts
    }


def handle_create_absence(employe: str, date: str, type_absence: str) -> dict:
    emp_info = next((e for e in EMPLOYES if e["nom"].lower() == employe.lower()), None)
    if not emp_info:
        return {"succes": False, "erreur": f"Employé '{employe}' introuvable"}

    employe_nom = emp_info["nom"]
    store = load_store()

    # Vérifier si absence déjà enregistrée pour cette date
    existante = next(
        (a for a in store["absences"] if a["employe"] == employe_nom and a["date"] == date),
        None
    )
    if existante:
        return {"succes": False, "erreur": f"Une absence est déjà enregistrée pour {employe_nom} le {date} (statut: {existante['statut']})"}

    # Vérifier solde congés si congé payé
    if type_absence == "Congé payé" and emp_info["jours_conge_restants"] <= 0:
        return {"succes": False, "erreur": f"{employe_nom} n'a plus de jours de congés disponibles (solde: {emp_info['jours_conge_restants']}j)"}

    nouvelle_absence = {
        "employe": employe_nom,
        "date": date,
        "type": type_absence,
        "statut": "En attente",
        "remplacant": None
    }
    store["absences"].append(nouvelle_absence)
    log_action(store, "create_absence", nouvelle_absence)
    save_store(store)

    return {
        "succes": True,
        "message": f"Demande d'absence créée pour {employe_nom} le {date} ({type_absence}). Statut: En attente.",
        "absence": nouvelle_absence
    }


def handle_approve_absence(employe: str, date: str) -> dict:
    store = load_store()

    absence = next(
        (a for a in store["absences"] if a["employe"] == employe and a["date"] == date),
        None
    )
    if not absence:
        return {"succes": False, "erreur": f"Aucune absence trouvée pour {employe} le {date}"}
    if absence["statut"] == "Validée":
        return {"succes": False, "erreur": f"Cette absence est déjà validée (remplaçant: {absence['remplacant']})"}

    # Trouver le meilleur remplaçant via le moteur de règles
    # Convertir la date en jour de la semaine
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        jour = jours_fr[date_obj.weekday()]
    except Exception:
        jour = "lundi"

    suggestions = suggest_replacement(employe, jour, "matin")
    remplacant = suggestions[0]["nom"] if suggestions else None

    absence["statut"] = "Validée"
    absence["remplacant"] = remplacant

    log_action(store, "approve_absence", {
        "employe": employe, "date": date, "remplacant": remplacant
    })
    save_store(store)

    if remplacant:
        return {
            "succes": True,
            "message": f"Absence de {employe} le {date} approuvée. Remplaçant assigné: {remplacant}.",
            "absence": absence,
            "remplacant": remplacant
        }
    else:
        emp_info = next((e for e in EMPLOYES if e["nom"] == employe), {})
        est_pde = emp_info.get("qualifie", False)
        alerte = " ⚠️ CRITIQUE: aucun PDE disponible pour remplacer — contacter un remplaçant externe." if est_pde else ""
        return {
            "succes": True,
            "message": f"Absence approuvée mais aucun remplaçant disponible le {jour}.{alerte}",
            "absence": absence,
            "remplacant": None
        }


def handle_reject_absence(employe: str, date: str, motif: str = "") -> dict:
    store = load_store()

    absence = next(
        (a for a in store["absences"] if a["employe"] == employe and a["date"] == date),
        None
    )
    if not absence:
        return {"succes": False, "erreur": f"Aucune absence trouvée pour {employe} le {date}"}
    if absence["statut"] == "Validée":
        return {"succes": False, "erreur": "Impossible de rejeter une absence déjà validée."}

    absence["statut"] = "Refusée"
    if motif:
        absence["motif_refus"] = motif

    log_action(store, "reject_absence", {"employe": employe, "date": date, "motif": motif})
    save_store(store)

    msg = f"Absence de {employe} le {date} refusée."
    if motif:
        msg += f" Motif: {motif}"
    return {"succes": True, "message": msg, "absence": absence}


def handle_get_absences(statut: str = None) -> dict:
    store = load_store()
    absences = store["absences"]
    if statut:
        absences = [a for a in absences if a["statut"] == statut]
    return {"absences": absences, "total": len(absences)}


def handle_run_compliance_check() -> dict:
    rapport = run_full_compliance_check()
    r = rapport["rapport"]
    return {
        "score_conformite": r["score_conformite"],
        "violations_critiques": len(rapport["violations_critiques"]),
        "violations_mineures": len(rapport["violations_mineures"]),
        "details_critiques": [v["message"] for v in rapport["violations_critiques"]],
        "details_mineures": [v["message"] for v in rapport["violations_mineures"]]
    }


# ═════════════════════════════════════════════
#  DISPATCHER — routage des appels d'outils
# ═════════════════════════════════════════════

def execute_tool(tool_name: str, tool_args: dict) -> str:
    """
    Reçoit le nom et les arguments d'un tool call Groq,
    exécute le bon handler, retourne le résultat en JSON string.
    """
    handlers = {
        "get_planning": lambda a: handle_get_planning(**a),
        "modify_planning": lambda a: handle_modify_planning(**a),
        "generate_planning": lambda a: handle_generate_planning(**a),
        "create_absence": lambda a: handle_create_absence(**a),
        "approve_absence": lambda a: handle_approve_absence(**a),
        "reject_absence": lambda a: handle_reject_absence(**a),
        "get_absences": lambda a: handle_get_absences(**a),
        "run_compliance_check": lambda a: handle_run_compliance_check(),
    }

    handler = handlers.get(tool_name)
    if not handler:
        return json.dumps({"erreur": f"Outil '{tool_name}' inconnu"}, ensure_ascii=False)

    try:
        result = handler(tool_args)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"erreur": str(e)}, ensure_ascii=False)