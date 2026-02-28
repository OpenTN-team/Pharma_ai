"""
rules_engine.py — Moteur de règles RH pour pharmacies
Convention Collective Pharmacie — IDCC 1996

Ce module effectue des vérifications de conformité sur les données de planning
et retourne des résultats structurés consommables par le chatbot ou l'UI.
"""

from datetime import datetime, date
from typing import Optional
import json

# ─────────────────────────────────────────────
#  Import des données (adapter selon votre projet)
# ─────────────────────────────────────────────
from data import EMPLOYES, PLANNING_SEMAINE, ABSENCES, ALERTES, METRIQUES, PHARMACIE

# ─────────────────────────────────────────────
#  CONSTANTES LÉGALES — IDCC 1996
# ─────────────────────────────────────────────
HEURES_LEGALES_SEMAINE = 35
MAX_HEURES_JOUR = 10
CONGES_MIN_ANNUELS = 25          # jours ouvrés
JOURS_OUVERTURE = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
JOURS_REPOS_OBLIGATOIRES = ["dimanche"]
DUREE_SHIFT_MATIN = 4            # heures estimées
DUREE_SHIFT_APRES_MIDI = 4       # heures estimées


# ═════════════════════════════════════════════
#  TYPES DE RÉSULTATS
# ═════════════════════════════════════════════

def _violation(code: str, message: str, niveau: str, details: dict = None) -> dict:
    """Crée une violation structurée."""
    return {
        "type": "violation",
        "code": code,
        "message": message,
        "niveau": niveau,          # "rouge" | "orange" | "vert"
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }

def _ok(code: str, message: str, details: dict = None) -> dict:
    """Crée un résultat de conformité positif."""
    return {
        "type": "ok",
        "code": code,
        "message": message,
        "niveau": "vert",
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }


# ═════════════════════════════════════════════
#  RÈGLE 1 — Présence d'un PDE à chaque shift
# ═════════════════════════════════════════════

def check_pde_presence() -> list[dict]:
    """
    Vérifie qu'un pharmacien diplômé d'État (PDE) est présent
    à chaque créneau d'ouverture (matin et après-midi).
    Règle OBLIGATOIRE selon le Code de la Santé Publique.
    """
    results = []
    pde_noms = {e["nom"] for e in EMPLOYES if e["qualifie"]}

    for jour, shifts in PLANNING_SEMAINE.items():
        for shift, employes in shifts.items():
            pde_presents = [e for e in employes if e in pde_noms]

            if not pde_presents:
                results.append(_violation(
                    code="PDE_ABSENT",
                    message=f"Aucun pharmacien diplômé (PDE) présent le {jour} — {shift.replace('_', ' ')}",
                    niveau="rouge",
                    details={"jour": jour, "shift": shift, "equipe_presente": employes}
                ))
            else:
                results.append(_ok(
                    code="PDE_PRESENT",
                    message=f"PDE présent le {jour} — {shift.replace('_', ' ')} : {', '.join(pde_presents)}",
                    details={"jour": jour, "shift": shift, "pde": pde_presents}
                ))

    return results


# ═════════════════════════════════════════════
#  RÈGLE 2 — Heures hebdomadaires légales
# ═════════════════════════════════════════════

def check_heures_semaine() -> list[dict]:
    """
    Vérifie que chaque employé ne dépasse pas 35h/semaine contractuelles
    et que les heures planifiées sont cohérentes avec leur contrat.
    """
    results = []

    # Calculer les shifts planifiés par employé cette semaine
    shifts_par_employe: dict[str, int] = {}
    for jour, shifts in PLANNING_SEMAINE.items():
        for shift, employes in shifts.items():
            for nom in employes:
                shifts_par_employe[nom] = shifts_par_employe.get(nom, 0) + 1

    heures_par_employe = {nom: count * 4 for nom, count in shifts_par_employe.items()}

    for employe in EMPLOYES:
        nom = employe["nom"]
        heures_planifiees = heures_par_employe.get(nom, 0)
        heures_contrat = employe["heures_semaine"]

        if heures_planifiees > HEURES_LEGALES_SEMAINE:
            results.append(_violation(
                code="DEPASSEMENT_HEURES",
                message=f"{nom} dépasse la durée légale : {heures_planifiees}h planifiées (max {HEURES_LEGALES_SEMAINE}h)",
                niveau="rouge",
                details={"employe": nom, "heures_planifiees": heures_planifiees, "limite": HEURES_LEGALES_SEMAINE}
            ))
        elif heures_planifiees < heures_contrat * 0.8:
            results.append(_violation(
                code="SOUS_PLANIFIE",
                message=f"{nom} est sous-planifié : {heures_planifiees}h sur {heures_contrat}h contractuelles",
                niveau="orange",
                details={"employe": nom, "heures_planifiees": heures_planifiees, "heures_contrat": heures_contrat}
            ))
        else:
            results.append(_ok(
                code="HEURES_OK",
                message=f"{nom} : {heures_planifiees}h planifiées — conforme",
                details={"employe": nom, "heures_planifiees": heures_planifiees}
            ))

    return results


# ═════════════════════════════════════════════
#  RÈGLE 3 — Absences non couvertes
# ═════════════════════════════════════════════

def check_absences_couvertes() -> list[dict]:
    """
    Vérifie que chaque absence enregistrée a un remplaçant assigné
    et que ce remplaçant est disponible et qualifié si nécessaire.
    """
    results = []

    employe_map = {e["nom"]: e for e in EMPLOYES}

    for absence in ABSENCES:
        nom = absence["employe"]
        remplacant = absence["remplacant"]
        date_absence = absence["date"]
        statut = absence["statut"]

        employe_absent = employe_map.get(nom, {})
        est_pde = employe_absent.get("qualifie", False)

        if remplacant is None:
            results.append(_violation(
                code="ABSENCE_NON_COUVERTE",
                message=f"{nom} absent(e) le {date_absence} ({absence['type']}) — aucun remplaçant assigné",
                niveau="rouge",
                details={
                    "employe": nom,
                    "date": date_absence,
                    "type_absence": absence["type"],
                    "statut": statut,
                    "pde_requis": est_pde
                }
            ))
        else:
            # Vérifier que le remplaçant est qualifié si l'absent est PDE
            remplacant_info = employe_map.get(remplacant, {})
            remplacant_qualifie = remplacant_info.get("qualifie", False)

            if est_pde and not remplacant_qualifie:
                results.append(_violation(
                    code="REMPLACANT_NON_QUALIFIE",
                    message=f"Remplacement invalide : {remplacant} n'est pas PDE pour remplacer {nom} (PDE) le {date_absence}",
                    niveau="rouge",
                    details={"employe_absent": nom, "remplacant": remplacant, "date": date_absence}
                ))
            else:
                results.append(_ok(
                    code="ABSENCE_COUVERTE",
                    message=f"Absence de {nom} le {date_absence} couverte par {remplacant}",
                    details={"employe": nom, "remplacant": remplacant, "date": date_absence}
                ))

    return results


# ═════════════════════════════════════════════
#  RÈGLE 4 — Solde de congés payés
# ═════════════════════════════════════════════

def check_conges_payes() -> list[dict]:
    """
    Vérifie que chaque employé dispose d'un solde de congés payés
    suffisant et signale les soldes critiquement bas.
    """
    results = []

    for employe in EMPLOYES:
        solde = employe["jours_conge_restants"]
        nom = employe["nom"]

        if solde == 0:
            results.append(_violation(
                code="CONGES_EPUISES",
                message=f"{nom} n'a plus de jours de congés disponibles",
                niveau="rouge",
                details={"employe": nom, "solde": solde}
            ))
        elif solde <= 3:
            results.append(_violation(
                code="CONGES_CRITIQUES",
                message=f"{nom} a un solde de congés très bas : {solde} jour(s) restant(s)",
                niveau="orange",
                details={"employe": nom, "solde": solde}
            ))
        else:
            results.append(_ok(
                code="CONGES_OK",
                message=f"{nom} : {solde} jour(s) de congés restants",
                details={"employe": nom, "solde": solde}
            ))

    return results


# ═════════════════════════════════════════════
#  RÈGLE 5 — Respect des disponibilités déclarées
# ═════════════════════════════════════════════

def check_disponibilites() -> list[dict]:
    """
    Vérifie que les employés ne sont pas planifiés sur des jours
    où ils ne sont pas disponibles selon leurs préférences déclarées.
    """
    results = []
    employe_map = {e["nom"]: e for e in EMPLOYES}

    for jour, shifts in PLANNING_SEMAINE.items():
        tous_employes_jour = set()
        for shift_employes in shifts.values():
            tous_employes_jour.update(shift_employes)

        for nom in tous_employes_jour:
            employe = employe_map.get(nom)
            if not employe:
                continue
            if jour not in employe["disponibilites"]:
                results.append(_violation(
                    code="HORS_DISPONIBILITE",
                    message=f"{nom} planifié(e) le {jour} mais non disponible ce jour",
                    niveau="orange",
                    details={"employe": nom, "jour": jour, "disponibilites": employe["disponibilites"]}
                ))

    return results


# ═════════════════════════════════════════════
#  RÈGLE 6 — Taux de couverture minimum
# ═════════════════════════════════════════════

def check_taux_couverture() -> list[dict]:
    """
    Vérifie que le taux de couverture hebdomadaire est acceptable (≥ 90%).
    """
    taux = METRIQUES["taux_couverture"]

    if taux < 85:
        return [_violation(
            code="COUVERTURE_CRITIQUE",
            message=f"Taux de couverture critique : {taux}% (seuil minimum : 85%)",
            niveau="rouge",
            details={"taux": taux, "seuil": 85}
        )]
    elif taux < 95:
        return [_violation(
            code="COUVERTURE_INSUFFISANTE",
            message=f"Taux de couverture insuffisant : {taux}% (recommandé : ≥ 95%)",
            niveau="orange",
            details={"taux": taux, "seuil_recommande": 95}
        )]
    else:
        return [_ok(
            code="COUVERTURE_OK",
            message=f"Taux de couverture satisfaisant : {taux}%",
            details={"taux": taux}
        )]


# ═════════════════════════════════════════════
#  MOTEUR PRINCIPAL — Rapport complet
# ═════════════════════════════════════════════

def run_full_compliance_check() -> dict:
    """
    Lance toutes les règles et retourne un rapport de conformité complet.
    C'est la fonction principale à appeler depuis le chatbot ou l'UI.
    """
    all_results = []
    all_results += check_pde_presence()
    all_results += check_heures_semaine()
    all_results += check_absences_couvertes()
    all_results += check_conges_payes()
    all_results += check_disponibilites()
    all_results += check_taux_couverture()

    violations_rouge = [r for r in all_results if r["niveau"] == "rouge" and r["type"] == "violation"]
    violations_orange = [r for r in all_results if r["niveau"] == "orange" and r["type"] == "violation"]
    conformes = [r for r in all_results if r["type"] == "ok"]

    score = round((len(conformes) / len(all_results)) * 100) if all_results else 100

    return {
        "rapport": {
            "pharmacie": PHARMACIE["nom"],
            "date_analyse": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "score_conformite": score,
            "total_verifications": len(all_results),
            "violations_critiques": len(violations_rouge),
            "violations_mineures": len(violations_orange),
            "conformes": len(conformes),
        },
        "violations_critiques": violations_rouge,
        "violations_mineures": violations_orange,
        "points_conformes": conformes,
        "toutes_verifications": all_results
    }


def get_summary_for_chatbot() -> str:
    """
    Retourne un résumé textuel du rapport de conformité,
    prêt à être injecté dans le contexte du chatbot.
    """
    rapport = run_full_compliance_check()
    r = rapport["rapport"]

    lignes = [
        f"=== RAPPORT DE CONFORMITÉ RH — {r['pharmacie']} ===",
        f"Date : {r['date_analyse']}",
        f"Score de conformité : {r['score_conformite']}%",
        f"Vérifications : {r['total_verifications']} | ✅ {r['conformes']} OK | 🔴 {r['violations_critiques']} critiques | 🟠 {r['violations_mineures']} mineures",
        ""
    ]

    if rapport["violations_critiques"]:
        lignes.append("🔴 VIOLATIONS CRITIQUES :")
        for v in rapport["violations_critiques"]:
            lignes.append(f"  [{v['code']}] {v['message']}")
        lignes.append("")

    if rapport["violations_mineures"]:
        lignes.append("🟠 VIOLATIONS MINEURES :")
        for v in rapport["violations_mineures"]:
            lignes.append(f"  [{v['code']}] {v['message']}")
        lignes.append("")

    return "\n".join(lignes)


# ═════════════════════════════════════════════
#  UTILITAIRES — Suggestions de remplacement
# ═════════════════════════════════════════════

def suggest_replacement(employe_absent: str, jour: str, shift: str) -> list[dict]:
    """
    Suggère des remplaçants disponibles pour un employé absent
    un jour et shift donnés.

    Args:
        employe_absent: Nom de l'employé absent
        jour: Jour de la semaine (ex: "lundi")
        shift: "matin" ou "apres_midi"

    Returns:
        Liste de remplaçants potentiels triés par priorité
    """
    absent_info = next((e for e in EMPLOYES if e["nom"] == employe_absent), None)
    if not absent_info:
        return []

    besoin_pde = absent_info["qualifie"]

    # Qui est déjà planifié ce jour-là ?
    deja_planifies = set()
    if jour in PLANNING_SEMAINE:
        for s, employes in PLANNING_SEMAINE[jour].items():
            deja_planifies.update(employes)

    suggestions = []
    for employe in EMPLOYES:
        if employe["nom"] == employe_absent:
            continue
        if employe["nom"] in deja_planifies:
            continue
        if jour not in employe["disponibilites"]:
            continue
        if besoin_pde and not employe["qualifie"]:
            continue

        # Score de priorité
        score = 0
        if employe["qualifie"]:
            score += 10
        if employe["jours_conge_restants"] > 5:
            score += 5
        if len(employe["disponibilites"]) >= 5:
            score += 3

        suggestions.append({
            "nom": employe["nom"],
            "role": employe["role"],
            "score_priorite": score,
            "jours_conge_restants": employe["jours_conge_restants"],
            "disponibilites": employe["disponibilites"]
        })

    return sorted(suggestions, key=lambda x: x["score_priorite"], reverse=True)


# ─────────────────────────────────────────────
#  Point d'entrée pour test rapide
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(get_summary_for_chatbot())
    print("\n--- Test suggest_replacement ---")
    suggestions = suggest_replacement("Karim Benali", "lundi", "matin")
    for s in suggestions:
        print(f"  → {s['nom']} ({s['role']}) — score: {s['score_priorite']}")