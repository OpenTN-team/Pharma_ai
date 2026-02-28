"""
agent.py — Agent PharmAssist avec tool calling Groq

Deux modes:
  - MODE MANAGER  : accès complet RH (planning, absences, conformité, etc.)
  - MODE EMPLOYÉ  : vue limitée (mes shifts, mes absences, mes notifications, demande de congé)
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv
from data import get_contexte_complet
from Rulesengine import get_summary_for_chatbot
from tools import TOOLS_SCHEMA, execute_tool

load_dotenv()


def configurer_gemini():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY introuvable. Vérifiez votre fichier .env")
    return Groq(api_key=api_key)


# ─────────────────────────────────────────────
# SYSTEM PROMPTS
# ─────────────────────────────────────────────

def _build_manager_prompt() -> str:
    return f"""Tu es PharmAssist, un agent RH intelligent pour la Pharmacie des Lilas à Lyon.

TES RESPONSABILITÉS (mode manager):
1. Gérer les plannings en respectant la Convention Collective Pharmacie (IDCC 1996)
2. Traiter les demandes d'absence : création, approbation, rejet
3. Anticiper les surcharges et alerter proactivement
4. Garantir qu'un PDE est TOUJOURS présent à chaque créneau
5. Respecter les 35h/semaine et les disponibilités

RÈGLES ABSOLUES (IDCC 1996):
- JAMAIS de créneau sans pharmacien diplômé (PDE)
- Maximum 10h/jour par employé
- Congés: 25 jours ouvrés minimum/an

COMMENT AGIR:
- Utilise TOUJOURS les outils pour effectuer des actions (ne décris pas, agis)
- Confirme chaque action effectuée avec son résultat
- Refuse toute action qui violerait une règle légale, cite la règle
- Pour les plannings récurrents: sauvegarde d'abord avec save_planning_as_reference

DONNÉES EN TEMPS RÉEL:
{get_contexte_complet()}

RAPPORT DE CONFORMITÉ:
{get_summary_for_chatbot()}

STYLE: Français, précis, professionnel."""


def _build_employee_prompt(nom_employe: str) -> str:
    """
    Prompt restreint pour un employé.
    L'agent ne peut PAS accéder aux données RH des autres.
    """
    return f"""Tu es PharmAssist, l'assistant RH de la Pharmacie des Lilas à Lyon.
Tu parles avec {nom_employe}, un(e) membre de l'équipe.

TES CAPACITÉS en mode employé:
- Consulter les shifts de la semaine de {nom_employe}
- Consulter les absences de {nom_employe}
- Créer une demande d'absence pour {nom_employe}
- Lire les notifications de {nom_employe}
- Répondre aux questions générales (règles légales, congés, etc.)

RESTRICTIONS IMPORTANTES:
- Tu ne peux PAS afficher le planning complet de l'équipe
- Tu ne peux PAS approuver ou rejeter des absences (rôle manager uniquement)
- Tu ne peux PAS modifier le planning
- Tu ne dois PAS révéler les informations personnelles des autres employés

Quand {nom_employe} demande ses shifts, utilise get_employee_schedule avec employe="{nom_employe}".
Quand {nom_employe} demande ses notifications, utilise get_notifications avec employe="{nom_employe}".
Quand {nom_employe} veut poser un congé, utilise create_absence avec employe="{nom_employe}".

STYLE: Chaleureux, clair, concis. Réponds en français."""


# ─────────────────────────────────────────────
# BOUCLE TOOL CALLING COMMUNE
# ─────────────────────────────────────────────

def _run_tool_loop(client: Groq, system_prompt: str, historique: list) -> tuple[str, list]:
    """
    Exécute la boucle tool calling complète.
    Retourne (reponse_finale, actions_effectuees).
    """
    actions_effectuees = []
    messages = [{"role": "system", "content": system_prompt}] + historique

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

        if finish_reason == "stop" or not message.tool_calls:
            reponse_finale = message.content or ""
            historique.append({"role": "assistant", "content": reponse_finale})
            return reponse_finale, actions_effectuees

        # Ajouter le message assistant avec tool_calls
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in message.tool_calls
            ]
        })

        # Exécuter chaque outil
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

    # Conclusion après épuisement des tours
    messages.append({"role": "user", "content": "Résume les actions effectuées."})
    final = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )
    reponse_finale = final.choices[0].message.content or ""
    historique.append({"role": "assistant", "content": reponse_finale})
    return reponse_finale, actions_effectuees


# ─────────────────────────────────────────────
# POINTS D'ENTRÉE PUBLICS
# ─────────────────────────────────────────────

def chat_avec_agent(client: Groq, historique: list, message_user: str) -> tuple[str, list]:
    """Mode manager — accès complet."""
    historique.append({"role": "user", "content": message_user})
    return _run_tool_loop(client, _build_manager_prompt(), historique)


def chat_employe(client: Groq, historique: list, message_user: str, nom_employe: str) -> tuple[str, list]:
    """Mode employé — accès restreint à ses propres données."""
    historique.append({"role": "user", "content": message_user})
    return _run_tool_loop(client, _build_employee_prompt(nom_employe), historique)