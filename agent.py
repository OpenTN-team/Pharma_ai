import google.generativeai as genai
from data import get_contexte_complet, EMPLOYES, ABSENCES, PLANNING_SEMAINE

def configurer_gemini(api_key: str):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        system_instruction=f"""
Tu es PharmAssist, un agent RH intelligent spécialisé pour les pharmacies françaises.
Tu travailles pour la Pharmacie des Lilas à Lyon.

TES RESPONSABILITÉS:
1. Gérer les plannings des employés en respectant la Convention Collective Pharmacie (IDCC 1996)
2. Traiter les demandes d'absence et proposer des remplaçants qualifiés
3. Anticiper les périodes de surcharge (début de mois, épidémies saisonnières)
4. Garantir qu'un Pharmacien Diplômé d'État (PDE) est TOUJOURS présent à l'ouverture
5. Respecter les 35h/semaine et le repos obligatoire

RÈGLES ABSOLUES:
- JAMAIS de créneau sans pharmacien diplômé (PDE)
- Maximum 10h de travail par jour par employé
- Respecter les disponibilités de chaque employé
- Prioriser les remplaçants disponibles et qualifiés

DONNÉES EN TEMPS RÉEL:
{get_contexte_complet()}

STYLE DE RÉPONSE:
- Réponds toujours en français
- Sois précis, professionnel et bienveillant
- Indique toujours la règle légale appliquée quand tu prends une décision
- Si une absence crée un problème de couverture PDE, signale-le en ALERTE
- Formate tes réponses clairement avec des sections quand nécessaire
        """
    )
    return model


def trouver_remplacant(employe_absent: str, jour: str) -> dict:
    employe_info = next((e for e in EMPLOYES if e["nom"] == employe_absent), None)
    if not employe_info:
        return {"succes": False, "message": "Employé introuvable"}

    est_pde = employe_info["qualifie"]
    candidats = []
    for emp in EMPLOYES:
        if emp["nom"] == employe_absent:
            continue
        if jour.lower() not in emp["disponibilites"]:
            continue
        if est_pde and not emp["qualifie"]:
            continue
        candidats.append(emp)

    if not candidats:
        if est_pde:
            return {
                "succes": False,
                "alerte": "ALERTE CRITIQUE: Aucun pharmacien diplômé disponible !",
                "message": "Impossible de couvrir ce créneau — contacter un remplaçant externe."
            }
        return {"succes": False, "message": "Aucun remplaçant disponible"}

    meilleur = min(candidats, key=lambda x: x["heures_semaine"])
    return {
        "succes": True,
        "remplacant": meilleur["nom"],
        "role": meilleur["role"],
        "message": f"{meilleur['nom']} ({meilleur['role']}) peut remplacer {employe_absent} le {jour}"
    }


def chat_avec_agent(model, historique: list, message_user: str) -> str:
    try:
        mots_absence = ["absent", "absente", "malade", "conge", "remplacer", "remplacement"]
        message_enrichi = message_user

        if any(mot in message_user.lower() for mot in mots_absence):
            for emp in EMPLOYES:
                prenom = emp["nom"].split()[0]
                if prenom.lower() in message_user.lower():
                    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
                    jour_trouve = next((j for j in jours if j in message_user.lower()), "lundi")
                    resultat = trouver_remplacant(emp["nom"], jour_trouve)
                    message_enrichi = f"{message_user}\n\n[ANALYSE SYSTEME: Employe={emp['nom']}, Role={emp['role']}, Resultat={resultat}]"
                    break

        historique.append({
            "role": "user",
            "parts": [{"text": message_enrichi}]
        })

        chat = model.start_chat(history=historique[:-1])
        response = chat.send_message(message_enrichi)
        reponse_text = response.text

        historique.append({
            "role": "model",
            "parts": [{"text": reponse_text}]
        })

        return reponse_text

    except Exception as e:
        return f"Erreur: {str(e)}"