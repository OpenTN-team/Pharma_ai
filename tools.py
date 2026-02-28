"""
tools.py — Définition et exécution des outils de l'agent PharmAssist

Outils disponibles:
  1.  get_planning               — Lire le planning courant
  2.  modify_planning            — Ajouter/retirer un employé d'un shift
  3.  generate_planning          — Générer un planning valide pour une semaine
  4.  create_absence             — Enregistrer une demande d'absence
  5.  approve_absence            — Approuver + déduire congés + notifier remplaçant
  6.  reject_absence             — Rejeter + restituer congés si applicable
  7.  get_absences               — Lister toutes les absences
  8.  run_compliance_check       — Lancer le moteur de règles
  9.  save_planning_as_reference — Sauvegarder le planning courant comme référence récurrente
  10. apply_reference_planning   — Appliquer le planning de référence à la semaine courante
  11. get_employee_schedule      — Vue employé : ses shifts de la semaine
  12. get_notifications          — Récupérer les notifications d'un employé
"""

import json
from datetime import datetime
from copy import deepcopy
from data import EMPLOYES
from store import (
    load_store, save_store, log_action,
    deduire_conge, restituer_conge,
    add_notification, get_notifications as store_get_notifications
)
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
                        "description": "Jour optionnel. Si absent, retourne toute la semaine.",
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
                    "employe": {"type": "string", "description": "Nom complet de l'employé"},
                    "jour": {
                        "type": "string",
                        "enum": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
                    },
                    "shift": {"type": "string", "enum": ["matin", "apres_midi"]},
                    "action": {"type": "string", "enum": ["ajouter", "retirer"]}
                },
                "required": ["employe", "jour", "shift", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_planning",
            "description": "Génère automatiquement un planning valide (PDE obligatoire, disponibilités, 35h max).",
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
                    "employe": {"type": "string"},
                    "date": {"type": "string", "description": "Format YYYY-MM-DD"},
                    "type_absence": {
                        "type": "string",
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
            "description": "Approuve une absence, déduit les congés si applicable, notifie le remplaçant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employe": {"type": "string"},
                    "date": {"type": "string", "description": "Format YYYY-MM-DD"}
                },
                "required": ["employe", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reject_absence",
            "description": "Rejette une demande d'absence et restitue les congés si déjà déduits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employe": {"type": "string"},
                    "date": {"type": "string", "description": "Format YYYY-MM-DD"},
                    "motif": {"type": "string", "description": "Raison du refus (optionnel)"}
                },
                "required": ["employe", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_absences",
            "description": "Retourne la liste des absences, filtrable par statut.",
            "parameters": {
                "type": "object",
                "properties": {
                    "statut": {
                        "type": "string",
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
            "description": "Lance le moteur de règles et retourne le rapport de conformité IDCC 1996.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_planning_as_reference",
            "description": "Sauvegarde le planning de la semaine courante comme planning de référence récurrent. Ce planning pourra être réappliqué chaque semaine.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_reference_planning",
            "description": "Applique le planning de référence à la semaine courante. Utile pour réinitialiser la semaine avec le planning habituel.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_schedule",
            "description": "Retourne les shifts d'un employé pour la semaine en cours. Utilisé pour la vue employé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employe": {"type": "string", "description": "Nom complet de l'employé"}
                },
                "required": ["employe"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_notifications",
            "description": "Récupère les notifications destinées à un employé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employe": {"type": "string", "description": "Nom complet de l'employé"}
                },
                "required": ["employe"]
            }
        }
    }
]


# ═════════════════════════════════════════════
#  HANDLERS
# ═════════════════════════════════════════════

def handle_get_planning(jour: str = None) -> dict:
    store = load_store()
    planning = store["planning"]
    if jour:
        return {"jour": jour, "planning": planning.get(jour, {})}
    return {"planning": planning}


def handle_modify_planning(employe: str, jour: str, shift: str, action: str) -> dict:
    emp_info = next((e for e in EMPLOYES if e["nom"].lower() == employe.lower()), None)
    if not emp_info:
        return {"succes": False, "erreur": f"Employé '{employe}' introuvable. Disponibles: {[e['nom'] for e in EMPLOYES]}"}

    employe_nom = emp_info["nom"]
    store = load_store()
    planning = store["planning"]

    if jour not in planning:
        planning[jour] = {"matin": [], "apres_midi": []}
    if shift not in planning[jour]:
        planning[jour][shift] = []

    equipe = planning[jour][shift]
    pde_noms = {e["nom"] for e in EMPLOYES if e["qualifie"]}

    if action == "ajouter":
        if employe_nom in equipe:
            return {"succes": False, "erreur": f"{employe_nom} est déjà planifié(e) le {jour} {shift}"}
        if jour not in emp_info["disponibilites"]:
            return {"succes": False, "erreur": f"{employe_nom} n'est pas disponible le {jour}"}
        equipe.append(employe_nom)
        # Notifier l'employé
        add_notification(store, employe_nom,
            f"Vous avez été ajouté(e) au planning : {jour} {shift.replace('_',' ')}.",
            "info")
        log_action(store, "modify_planning", {"action": "ajouter", "employe": employe_nom, "jour": jour, "shift": shift})
        save_store(store)
        return {"succes": True, "message": f"{employe_nom} ajouté(e) le {jour} {shift}", "equipe": equipe}

    elif action == "retirer":
        if employe_nom not in equipe:
            return {"succes": False, "erreur": f"{employe_nom} n'est pas planifié(e) le {jour} {shift}"}
        # Garde-fou PDE : refuser si c'est le dernier PDE du shift
        if employe_nom in pde_noms:
            autres_pde = [e for e in equipe if e in pde_noms and e != employe_nom]
            if not autres_pde:
                return {
                    "succes": False,
                    "erreur": f"VIOLATION CRITIQUE: {employe_nom} est le seul PDE le {jour} {shift}. Assignez d'abord un remplaçant PDE."
                }
        equipe.remove(employe_nom)
        add_notification(store, employe_nom,
            f"Votre shift du {jour} {shift.replace('_',' ')} a été modifié.",
            "warning")
        log_action(store, "modify_planning", {"action": "retirer", "employe": employe_nom, "jour": jour, "shift": shift})
        save_store(store)
        return {"succes": True, "message": f"{employe_nom} retiré(e) du {jour} {shift}", "equipe": equipe}

    return {"succes": False, "erreur": "Action invalide"}


def handle_generate_planning(remplacer_existant: bool) -> dict:
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
    pde = [e for e in EMPLOYES if e["qualifie"]]
    preparateurs = [e for e in EMPLOYES if not e["qualifie"]]
    planning_genere = {}
    compteur_shifts = {e["nom"]: 0 for e in EMPLOYES}
    max_shifts = {e["nom"]: (e["heures_semaine"] // 4) for e in EMPLOYES}

    for jour in jours:
        planning_genere[jour] = {"matin": [], "apres_midi": []}
        for shift in ["matin", "apres_midi"]:
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

            preps_dispo = [
                e for e in preparateurs
                if jour in e["disponibilites"]
                and compteur_shifts[e["nom"]] < max_shifts[e["nom"]]
                and e["nom"] not in planning_genere[jour][shift]
            ]
            preps_dispo.sort(key=lambda e: compteur_shifts[e["nom"]])
            nb_preps = 1 if jour == "mercredi" else 2
            for prep in preps_dispo[:nb_preps]:
                planning_genere[jour][shift].append(prep["nom"])
                compteur_shifts[prep["nom"]] += 1

    if remplacer_existant:
        store = load_store()
        store["planning"] = planning_genere
        # Notifier toute l'équipe
        add_notification(store, "TOUS",
            "Le planning de la semaine vient d'être mis à jour. Consultez vos shifts.",
            "info")
        log_action(store, "generate_planning", {"remplace": True, "shifts_par_employe": compteur_shifts})
        save_store(store)
        return {
            "succes": True,
            "message": "Planning généré et sauvegardé. L'équipe a été notifiée.",
            "planning": planning_genere,
            "shifts_par_employe": compteur_shifts
        }
    return {
        "succes": True,
        "message": "Proposition de planning (non sauvegardée). Confirmez pour l'appliquer.",
        "planning": planning_genere,
        "shifts_par_employe": compteur_shifts
    }


def handle_create_absence(employe: str, date: str, type_absence: str) -> dict:
    emp_info = next((e for e in EMPLOYES if e["nom"].lower() == employe.lower()), None)
    if not emp_info:
        return {"succes": False, "erreur": f"Employé '{employe}' introuvable"}

    employe_nom = emp_info["nom"]
    store = load_store()

    # Vérifier doublon
    existante = next(
        (a for a in store["absences"] if a["employe"] == employe_nom and a["date"] == date),
        None
    )
    if existante:
        return {"succes": False, "erreur": f"Absence déjà enregistrée le {date} (statut: {existante['statut']})"}

    # Vérifier solde depuis le STORE (pas data.py) — c'est la correction clé
    solde_actuel = store["employes_soldes"].get(employe_nom, 0)
    if type_absence == "Congé payé" and solde_actuel <= 0:
        return {"succes": False, "erreur": f"{employe_nom} n'a plus de congés (solde: {solde_actuel}j)"}

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
        "message": f"Demande créée pour {employe_nom} le {date} ({type_absence}). En attente de validation.",
        "absence": nouvelle_absence,
        "solde_restant": solde_actuel
    }


def handle_approve_absence(employe: str, date: str) -> dict:
    """
    Approuve une absence :
    1. Trouve l'absence dans le store
    2. Si Congé payé → déduit 1 jour du solde dans le store
    3. Trouve le meilleur remplaçant via rules engine
    4. Envoie une notification au remplaçant
    5. Envoie une notification à l'employé absent (confirmation)
    """
    store = load_store()

    absence = next(
        (a for a in store["absences"] if a["employe"] == employe and a["date"] == date),
        None
    )
    if not absence:
        return {"succes": False, "erreur": f"Aucune absence pour {employe} le {date}"}
    if absence["statut"] == "Validée":
        return {"succes": False, "erreur": f"Déjà validée (remplaçant: {absence['remplacant']})"}

    # ── ÉTAPE 1 : Déduction congés si Congé payé ──
    solde_apres = None
    if absence["type"] == "Congé payé":
        succes_deduction = deduire_conge(store, employe, jours=1)
        if not succes_deduction:
            solde_actuel = store["employes_soldes"].get(employe, 0)
            return {
                "succes": False,
                "erreur": f"Impossible d'approuver : solde congés insuffisant ({solde_actuel}j)"
            }
        solde_apres = store["employes_soldes"][employe]

    # ── ÉTAPE 2 : Trouver le remplaçant ──
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        jour = jours_fr[date_obj.weekday()]
    except Exception:
        jour = "lundi"

    suggestions = suggest_replacement(employe, jour, "matin")
    remplacant = suggestions[0]["nom"] if suggestions else None

    # ── ÉTAPE 3 : Mettre à jour l'absence ──
    absence["statut"] = "Validée"
    absence["remplacant"] = remplacant

    # ── ÉTAPE 4 : Notifications ──
    # Notifier l'employé absent
    add_notification(store, employe,
        f"Votre absence du {date} ({absence['type']}) a été approuvée."
        + (f" Solde congés restant : {solde_apres}j." if solde_apres is not None else ""),
        "success")

    # Notifier le remplaçant
    if remplacant:
        add_notification(store, remplacant,
            f"Vous êtes désigné(e) remplaçant(e) de {employe} le {date} ({jour}).",
            "urgent")

    # Notifier toute l'équipe si pas de remplaçant trouvé
    if not remplacant:
        emp_info = next((e for e in EMPLOYES if e["nom"] == employe), {})
        if emp_info.get("qualifie"):
            add_notification(store, "TOUS",
                f"URGENT: Aucun PDE disponible pour remplacer {employe} le {date}. Action requise.",
                "urgent")

    log_action(store, "approve_absence", {
        "employe": employe, "date": date,
        "remplacant": remplacant,
        "conge_deduit": absence["type"] == "Congé payé",
        "solde_apres": solde_apres
    })
    save_store(store)

    msg = f"Absence de {employe} le {date} approuvée."
    if remplacant:
        msg += f" Remplaçant: {remplacant} (notifié)."
    if solde_apres is not None:
        msg += f" Solde congés restant: {solde_apres}j."
    if not remplacant:
        emp_info = next((e for e in EMPLOYES if e["nom"] == employe), {})
        msg += " ⚠️ Aucun remplaçant disponible — action requise." if emp_info.get("qualifie") else " Aucun remplaçant disponible."

    return {
        "succes": True,
        "message": msg,
        "absence": absence,
        "remplacant": remplacant,
        "solde_apres_deduction": solde_apres
    }


def handle_reject_absence(employe: str, date: str, motif: str = "") -> dict:
    """
    Rejette une absence.
    Si le congé avait déjà été déduit (cas rare), le restitue.
    Notifie l'employé du refus avec le motif.
    """
    store = load_store()

    absence = next(
        (a for a in store["absences"] if a["employe"] == employe and a["date"] == date),
        None
    )
    if not absence:
        return {"succes": False, "erreur": f"Aucune absence pour {employe} le {date}"}
    if absence["statut"] == "Validée":
        return {"succes": False, "erreur": "Impossible de rejeter une absence déjà validée."}

    absence["statut"] = "Refusée"
    if motif:
        absence["motif_refus"] = motif

    # Notifier l'employé
    msg_notif = f"Votre demande d'absence du {date} a été refusée."
    if motif:
        msg_notif += f" Motif : {motif}."
    add_notification(store, employe, msg_notif, "warning")

    log_action(store, "reject_absence", {"employe": employe, "date": date, "motif": motif})
    save_store(store)

    msg = f"Absence de {employe} le {date} refusée."
    if motif:
        msg += f" Motif: {motif}."
    msg += " Employé notifié."
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


def handle_save_planning_as_reference() -> dict:
    """
    Sauvegarde le planning courant comme planning de référence.
    Ce planning servira de base pour les semaines récurrentes.
    """
    store = load_store()
    store["planning_reference"] = deepcopy(store["planning"])
    log_action(store, "save_planning_reference", {
        "jours_couverts": list(store["planning_reference"].keys())
    })
    save_store(store)
    return {
        "succes": True,
        "message": "Planning actuel sauvegardé comme référence récurrente. "
                   "Utilisez 'apply_reference_planning' chaque début de semaine pour l'appliquer.",
        "jours_couverts": list(store["planning_reference"].keys())
    }


def handle_apply_reference_planning() -> dict:
    """
    Applique le planning de référence à la semaine courante.
    C'est l'équivalent de 'copier la semaine dernière'.
    """
    store = load_store()

    if not store.get("planning_reference"):
        return {
            "succes": False,
            "erreur": "Aucun planning de référence enregistré. "
                      "Utilisez 'save_planning_as_reference' d'abord."
        }

    store["planning"] = deepcopy(store["planning_reference"])
    add_notification(store, "TOUS",
        "Le planning de la semaine a été réinitialisé avec le planning habituel.",
        "info")
    log_action(store, "apply_reference_planning", {
        "jours_appliques": list(store["planning"].keys())
    })
    save_store(store)

    return {
        "succes": True,
        "message": "Planning de référence appliqué à la semaine courante. Équipe notifiée.",
        "planning": store["planning"]
    }


def handle_get_employee_schedule(employe: str) -> dict:
    """
    Retourne uniquement les shifts d'un employé pour la semaine.
    Utilisé par la vue employé — ne retourne PAS le planning complet.
    """
    emp_info = next((e for e in EMPLOYES if e["nom"].lower() == employe.lower()), None)
    if not emp_info:
        return {"succes": False, "erreur": f"Employé '{employe}' introuvable"}

    employe_nom = emp_info["nom"]
    store = load_store()
    planning = store["planning"]
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]

    mes_shifts = []
    for jour in jours:
        matin = employe_nom in planning.get(jour, {}).get("matin", [])
        am    = employe_nom in planning.get(jour, {}).get("apres_midi", [])
        if matin and am:
            mes_shifts.append({"jour": jour, "shift": "Journée complète (Matin + Après-midi)"})
        elif matin:
            mes_shifts.append({"jour": jour, "shift": "Matin"})
        elif am:
            mes_shifts.append({"jour": jour, "shift": "Après-midi"})

    solde = store["employes_soldes"].get(employe_nom, 0)
    absences_employe = [a for a in store["absences"] if a["employe"] == employe_nom]

    return {
        "succes": True,
        "employe": employe_nom,
        "role": emp_info["role"],
        "shifts_semaine": mes_shifts,
        "total_shifts": len(mes_shifts),
        "solde_conges": solde,
        "mes_absences": absences_employe
    }


def handle_get_notifications(employe: str) -> dict:
    emp_info = next((e for e in EMPLOYES if e["nom"].lower() == employe.lower()), None)
    if not emp_info:
        return {"succes": False, "erreur": f"Employé '{employe}' introuvable"}

    notifications = store_get_notifications(emp_info["nom"])
    non_lues = [n for n in notifications if not n["lu"]]
    return {
        "succes": True,
        "employe": emp_info["nom"],
        "notifications": notifications,
        "non_lues": len(non_lues)
    }


# ═════════════════════════════════════════════
#  DISPATCHER
# ═════════════════════════════════════════════

def execute_tool(tool_name: str, tool_args: dict) -> str:
    handlers = {
        "get_planning":               lambda a: handle_get_planning(**a),
        "modify_planning":            lambda a: handle_modify_planning(**a),
        "generate_planning":          lambda a: handle_generate_planning(**a),
        "create_absence":             lambda a: handle_create_absence(**a),
        "approve_absence":            lambda a: handle_approve_absence(**a),
        "reject_absence":             lambda a: handle_reject_absence(**a),
        "get_absences":               lambda a: handle_get_absences(**a),
        "run_compliance_check":       lambda a: handle_run_compliance_check(),
        "save_planning_as_reference": lambda a: handle_save_planning_as_reference(),
        "apply_reference_planning":   lambda a: handle_apply_reference_planning(),
        "get_employee_schedule":      lambda a: handle_get_employee_schedule(**a),
        "get_notifications":          lambda a: handle_get_notifications(**a),
    }
    handler = handlers.get(tool_name)
    if not handler:
        return json.dumps({"erreur": f"Outil '{tool_name}' inconnu"}, ensure_ascii=False)
    try:
        result = handler(tool_args)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"erreur": str(e)}, ensure_ascii=False)