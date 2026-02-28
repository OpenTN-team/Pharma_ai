# PharmAssist – Assistant RH Intelligent pour Pharmacie d'Officine

Prototype d’interface RH spécialisée pour pharmacies françaises, conforme à la **Convention Collective Nationale de la Pharmacie d’officine (IDCC 1996)**.

Construit avec **Streamlit** et un agent IA qui combine logique déterministe (Python) et explications métier générées par LLM.

## Fonctionnalités actuelles

### Dashboard principal (Manager)
- Vue d’ensemble en temps réel :
  - Taux de couverture global (%)
  - Nombre d’employés actifs
  - Nombre de pharmaciens PDE
  - Absences ce mois
  - Alertes actives
  - Score de conformité IDCC 1996 (avec détails critiques/mineures)
- Métriques mises à jour dynamiquement via moteur de règles

### Gestion du planning
- Affichage clair du planning hebdomadaire (matin / après-midi par jour)
- Vue par employé : présence, rôle (PDE / Préparateur), heures contractuelles
- Graphiques d’effectif par jour (barres matin/après-midi)
- Comparaison heures planifiées vs légales (jauge)

### Gestion des employés
- Liste complète de l’équipe avec :
  - Avatar coloré selon rôle
  - Nom, rôle, disponibilités hebdomadaires
  - Heures contractuelles
  - Soldes de congés restants
- Formulaire rapide pour créer une demande d’absence (employé, date, type)
- Liste des absences en attente avec boutons Approuver / Rejeter directs

### Conformité & Violations (IDCC 1996)
- Rapport détaillé de conformité :
  - Score global (couleur selon gravité)
  - Nombre de vérifications, points conformes, violations critiques/mineures
  - Violations critiques listées (ex: absence non couverte, PDE manquant)
  - Violations mineures listées (ex: sous-planification, couverture insuffisante)
- Cercle de score visuel + camembert répartition (conforme / critique / mineure)

### Portail Employé (mode restreint)
- Sélection d’identité via sidebar (isolation stricte des données)
- Espace personnel :
  - Infos employé (nom, rôle, solde congés restant)
  - Chat dédié avec l’assistant RH (accès limité à ses propres données)
  - Suggestions rapides (mes shifts, mes absences, poser congé, notifications, droits)
  - Liste des notifications personnelles + broadcast (urgentes, info, succès, warning)
  - Planning personnel de la semaine (jours + type de shift)

### Agent IA conversationnel
- Mode Manager : accès complet (planning, absences, conformité)
- Mode Employé : vue très restreinte (seulement ses shifts, absences, notifications, demandes)
- Outils disponibles :
  - Consultation planning global / personnel
  - Création / approbation / rejet d’absences (avec déduction congés)
  - Modification planning (ajout/retrait shift)
  - Génération planning automatique
  - Sauvegarde / application planning de référence
  - Notifications ciblées ou broadcast
- Réponses en français professionnel, citations des règles IDCC 1996 quand pertinent

### Autres fonctionnalités intégrées
- Thème sombre/clair toggle (bouton en haut à droite)
- Historique complet des actions RH (avec timestamp et détails)
- Export PDF du planning et du rapport de conformité
- Notifications persistantes (stockées, marquage lu)
- Logs d’actions et persistance JSON

## Technologies utilisées

- **Interface** : Streamlit
- **Agent IA** : Groq + Llama 3.3 (ou Mistral / autre via OpenAI-compatible)
- **Stockage** : JSON simple (planning, absences, soldes congés, notifications, historique)
- **Règles métier** : Python pur (vérification conformité, recherche remplaçants)

## Installation rapide

```bash
git clone <votre-repo>
cd pharmassist
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
