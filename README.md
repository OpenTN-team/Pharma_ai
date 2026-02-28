# PharmAssist – Assistant RH Intelligent pour Pharmacie d'Officine

Prototype d’interface RH spécialisée pour pharmacies françaises, conforme à la **Convention Collective Nationale de la Pharmacie d’officine (IDCC 1996)**.

Construit avec **Streamlit** et un agent IA qui combine logique déterministe (Python) et explications métier générées par LLM via **Hugging Face Inference API**.

---

## 📁 Structure du projet

```
pharmassist/
├── .gitignore
├── README.md
├── Rulesengine.py
├── agent.py
├── app.py
├── data.py
├── pdf_export.py
├── pharmassist_store.json
├── requirements.txt
├── store.py
└── tools.py
```

### Description des fichiers

- `app.py` → Interface principale Streamlit (Dashboard, Planning, Portail Employé)
- `agent.py` → Agent IA conversationnel (Manager / Employé)
- `Rulesengine.py` → Moteur de règles métier & conformité IDCC 1996
- `tools.py` → Outils disponibles pour l’agent (planning, absences, notifications…)
- `store.py` → Gestion de la persistance JSON
- `data.py` → Données initiales & structures
- `pdf_export.py` → Génération PDF (planning + conformité)
- `pharmassist_store.json` → Stockage des données (planning, absences, logs…)
- `requirements.txt` → Dépendances Python

---

## 🚀 Fonctionnalités actuelles

### Dashboard principal (Manager)
- Vue d’ensemble en temps réel :
  - Taux de couverture global (%)
  - Nombre d’employés actifs
  - Nombre de pharmaciens PDE
  - Absences ce mois
  - Alertes actives
  - Score de conformité IDCC 1996 (détails critiques/mineures)
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
- Formulaire rapide pour créer une demande d’absence
- Liste des absences en attente avec boutons Approuver / Rejeter

### Conformité & Violations (IDCC 1996)
- Rapport détaillé :
  - Score global (couleur selon gravité)
  - Nombre de vérifications
  - Violations critiques
  - Violations mineures
- Cercle de score visuel + camembert de répartition

### Portail Employé (mode restreint)
- Sélection d’identité via sidebar (isolation stricte des données)
- Espace personnel :
  - Informations employé (nom, rôle, solde congés)
  - Chat RH dédié
  - Suggestions rapides
  - Notifications personnelles + broadcast
  - Planning personnel hebdomadaire

### Agent IA conversationnel
- Mode Manager : accès complet
- Mode Employé : accès restreint
- Outils disponibles :
  - Consultation planning global / personnel
  - Création / approbation / rejet d’absences
  - Modification planning
  - Génération planning automatique
  - Notifications ciblées ou broadcast
- Réponses professionnelles en français avec référence aux règles IDCC 1996 si pertinent

### Autres fonctionnalités
- Thème sombre/clair toggle
- Historique complet des actions RH (timestamp + détails)
- Export PDF planning & conformité
- Notifications persistantes
- Persistance JSON

---

## 🛠 Technologies utilisées

- **Interface** : Streamlit  
- **Agent IA** : Hugging Face Inference API  
- **Backend logique métier** : Python  
- **Stockage** : JSON  
- **Export PDF** : Python (génération locale)

---

## ⚙️ Installation

```bash
git clone <votre-repo>
cd pharmassist
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

---

## 🔐 Configuration API 

Créer un fichier `.env` à la racine du projet :

```env
HF_API_KEY=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 
```

Ou définir la variable d’environnement :

```bash
export HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxx   # Linux/Mac
set HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxx      # Windows
```

⚠️ Important :
- Ne jamais commit votre token sur GitHub
- Assurez-vous que `.env` est dans `.gitignore`

---

## ▶️ Lancement

```bash
streamlit run app.py
```

---

## 👨‍💻 Auteur

**Wassim Gasmi**  
**Maram Namouchi**  
Prototype RH IA pour pharmacie d’officine  
Hackathon 2026 – Tunis, Tunisie
