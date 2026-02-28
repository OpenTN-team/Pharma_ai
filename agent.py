import os
from groq import Groq
from dotenv import load_dotenv
from data import get_contexte_complet, EMPLOYES
from Rulesengine import get_summary_for_chatbot, suggest_replacement

# ============================================================
# CONFIGURATION — Chargement depuis .env
# ============================================================

load_dotenv()

def configurer_gemini():
    """Initialise le client Groq depuis la variable d'environnement GROQ_API_KEY."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY introuvable. Vérifiez votre fichier .env")
    client = Groq(api_key=api_key)
    return client


# ============================================================
# LOGIQUE DE REMPLACEMENT
# ============================================================

def trouver_remplacant(employe_absent: str, jour: str) -> dict:
    """Trouve le meilleur remplaçant via le moteur de règles."""
    suggestions = suggest_replacement(employe_absent, jour, "matin")  # shift par défaut

    if not suggestions:
        employe_info = next((e for e in EMPLOYES if e["nom"] == employe_absent), None)
        est_pde = employe_info["qualifie"] if employe_info else False
        if est_pde:
            return {
                "succes": False,
                "alerte": "ALERTE CRITIQUE: Aucun pharmacien diplômé disponible !",
                "message": "Impossible de couvrir ce créneau — contacter un remplaçant externe."
            }
        return {"succes": False, "message": "Aucun remplaçant disponible"}

    meilleur = suggestions[0]
    return {
        "succes": True,
        "remplacant": meilleur["nom"],
        "role": meilleur["role"],
        "message": f"{meilleur['nom']} ({meilleur['role']}) peut remplacer {employe_absent} le {jour}"
    }


# ============================================================
# AGENT CONVERSATIONNEL
# ============================================================

def chat_avec_agent(client, historique: list, message_user: str) -> str:
    try:
        # Détecter absence et enrichir le message avec analyse système
        mots_absence = ["absent", "absente", "malade", "conge", "congé", "remplacer", "remplacement"]
        message_enrichi = message_user

        if any(mot in message_user.lower() for mot in mots_absence):
            for emp in EMPLOYES:
                prenom = emp["nom"].split()[0]
                if prenom.lower() in message_user.lower():
                    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
                    jour_trouve = next((j for j in jours if j in message_user.lower()), "lundi")
                    resultat = trouver_remplacant(emp["nom"], jour_trouve)
                    message_enrichi = (
                        f"{message_user}\n\n"
                        f"[ANALYSE SYSTEME: Employe={emp['nom']}, Role={emp['role']}, Resultat={resultat}]"
                    )
                    break

        historique.append({"role": "user", "content": message_enrichi})

        # Rapport de conformité injecté dynamiquement à chaque appel
        compliance_summary = get_summary_for_chatbot()

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": f"""Tu es PharmAssist, un agent RH intelligent spécialisé pour les pharmacies françaises.
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

DONNÉES EN TEMPS RÉEL:
{get_contexte_complet()}

RAPPORT DE CONFORMITÉ (Moteur de règles — résultats en temps réel):
{compliance_summary}

STYLE: Réponds toujours en français, sois précis et professionnel.
Cite toujours la règle légale appliquée dans tes décisions.
Si des violations critiques sont présentes dans le rapport de conformité, mentionne-les proactivement."""
                }
            ] + historique,
            max_tokens=1024,
            temperature=0.7,
        )

        reponse_text = response.choices[0].message.content
        historique.append({"role": "assistant", "content": reponse_text})
        return reponse_text

    except Exception as e:
        return f"Erreur: {str(e)}"