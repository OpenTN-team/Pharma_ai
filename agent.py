"""
agent.py — Agent PharmAssist avec tool calling Groq
L'agent peut désormais agir : générer des plannings, créer/approuver des absences,
modifier des shifts, lancer des vérifications de conformité.
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv
from data import get_contexte_complet
from Rulesengine import get_summary_for_chatbot
from tools import TOOLS_SCHEMA, execute_tool

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

load_dotenv()

def configurer_gemini():
    """Initialise le client Groq depuis la variable d'environnement GROQ_API_KEY."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY introuvable. Vérifiez votre fichier .env")
    return Groq(api_key=api_key)


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

def _build_system_prompt() -> str:
    return f"""Tu es PharmAssist, un agent RH intelligent et autonome spécialisé pour les pharmacies françaises.
Tu travailles pour la Pharmacie des Lilas à Lyon.

TES RESPONSABILITÉS:
1. Gérer les plannings en respectant la Convention Collective Pharmacie (IDCC 1996)
2. Traiter les demandes d'absence : création, approbation, rejet
3. Anticiper les surcharges et alerter proactivement
4. Garantir qu'un Pharmacien Diplômé d'État (PDE) est TOUJOURS présent
5. Respecter les 35h/semaine et les disponibilités de chaque employé

RÈGLES ABSOLUES (IDCC 1996):
- JAMAIS de créneau sans pharmacien diplômé (PDE) — infraction légale
- Maximum 10h de travail par jour
- Repos hebdomadaire le dimanche obligatoire
- Congés payés: 25 jours ouvrés minimum par an

COMMENT AGIR:
- Quand on te demande d'effectuer une action (créer une absence, modifier un planning, etc.),
  utilise TOUJOURS l'outil approprié plutôt que de simplement décrire ce que tu ferais.
- Après chaque action, confirme ce qui a été fait et signale toute violation détectée.
- Si une action violerait une règle légale, REFUSE et explique pourquoi.
- Cite toujours la règle IDCC 1996 appliquée dans tes décisions.

DONNÉES EN TEMPS RÉEL:
{get_contexte_complet()}

RAPPORT DE CONFORMITÉ ACTUEL:
{get_summary_for_chatbot()}

STYLE: Français, précis, professionnel. Confirme chaque action effectuée clairement."""


# ─────────────────────────────────────────────
# BOUCLE TOOL CALLING
# ─────────────────────────────────────────────

def chat_avec_agent(client: Groq, historique: list, message_user: str) -> tuple[str, list]:
    """
    Envoie un message à l'agent et exécute la boucle tool calling complète.

    Returns:
        (reponse_finale: str, actions_effectuees: list)
        actions_effectuees contient les outils appelés et leurs résultats.
    """
    historique.append({"role": "user", "content": message_user})
    actions_effectuees = []

    messages = [{"role": "system", "content": _build_system_prompt()}] + historique

    # Boucle tool calling — max 5 tours pour éviter les boucles infinies
    for _ in range(5):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            max_tokens=2048,
            temperature=0.3,
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # Pas d'appel d'outil — réponse finale
        if finish_reason == "stop" or not message.tool_calls:
            reponse_finale = message.content or ""
            historique.append({"role": "assistant", "content": reponse_finale})
            return reponse_finale, actions_effectuees

        # L'agent veut appeler un ou plusieurs outils
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        })

        # Exécuter chaque outil et ajouter les résultats
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            tool_result = execute_tool(tool_name, tool_args)

            actions_effectuees.append({
                "outil": tool_name,
                "arguments": tool_args,
                "resultat": json.loads(tool_result)
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })

    # Épuisement des tours — demander une conclusion
    messages.append({"role": "user", "content": "Résume les actions effectuées et leur résultat."})
    final = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )
    reponse_finale = final.choices[0].message.content or ""
    historique.append({"role": "assistant", "content": reponse_finale})
    return reponse_finale, actions_effectuees