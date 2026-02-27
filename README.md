# Pharma_ai
Voici un **README complet, propre et professionnel** que vous pouvez copier directement dans votre projet (`README.md`).

---

# 💊 Assistant RH Intelligent – Pharmacie des Lilas

Prototype d’agent IA spécialisé en gestion RH pour pharmacie d’officine française.

Ce projet démontre comment un assistant IA peut :

* Gérer les absences
* Proposer des remplacements conformes
* Respecter les contraintes légales françaises
* Expliquer ses décisions en langage métier

⚠️ Il s’agit d’un **prototype démonstratif** (Proof of Concept), pas d’un produit final.

---

# 🎯 Objectif du Projet

Construire un agent RH intelligent capable de :

* Comprendre les contraintes métier d’une pharmacie française
* Appliquer des règles déterministes côté Python
* Utiliser un LLM uniquement pour l’explication métier
* Fournir une interface simple via Streamlit

Le projet est basé sur la réglementation française, notamment :

* Convention Collective Nationale de la pharmacie d'officine (IDCC 1996)
* Durée légale de 35h/semaine
* Maximum 10h/jour
* Présence obligatoire d’un Pharmacien Diplômé d’État (PDE)

---

# 🏗 Architecture du Projet

```
pharma_ai/
│
├── app.py
│
├── data/
│   ├── employees.json
│   ├── schedule.json
│   └── constraints.json
│
└── agent/
    ├── agent.py
    └── rules.py
```

---

# 📁 Description des Modules

## 1️⃣ `app.py`

Interface utilisateur via Streamlit.

Responsabilités :

* Affichage du dashboard
* Gestion des inputs utilisateur
* Appel des fonctions de l’agent
* Affichage des réponses

Ce fichier ne contient aucune logique métier.

---

## 2️⃣ `data/`

Contient toutes les données locales au format JSON.

### `employees.json`

Liste des employés de la pharmacie :

* Nom
* Rôle
* Statut PDE
* Heures contractuelles

### `schedule.json`

Planning hebdomadaire (initialement vide).

### `constraints.json`

Contraintes légales :

* Maximum hebdomadaire
* Maximum journalier
* Obligation PDE
* Référence convention collective

---

## 3️⃣ `agent/rules.py`

Logique métier déterministe (Python pur).

Responsabilités :

* Chargement des données
* Recherche de remplaçant
* Vérification basique des règles

⚠️ Aucune IA ici.

C’est le moteur décisionnel.

---

## 4️⃣ `agent/agent.py`

Couche IA.

Responsabilités :

* Appeler l’API OpenAI
* Générer une explication métier professionnelle
* Mentionner la réglementation française
* Reformuler les décisions prises par Python

⚠️ Le LLM explique, mais ne décide pas.

---

# 🧠 Cas d’Usage Implémentés

## ✅ Cas 1 — Gestion d’absence

Entrée :

```
Marie est absente
```

Processus :

1. Python identifie son rôle
2. Cherche un employé compatible
3. Vérifie contraintes basiques
4. Le LLM explique la décision

Sortie :
Explication conforme au droit du travail français.

---

## 🔜 Cas prévus (Phase suivante)

* Génération automatique de planning hebdomadaire
* Détection des périodes à risque (ex : période grippale)
* KPI RH (taux couverture, heures planifiées)

---

# ⚙️ Prérequis

* Python 3.9+
* Clé API OpenAI
* pip

---

# 📦 Installation

Clonez le projet :

```bash
git clone <repo_url>
cd pharma_ai
```

Installez les dépendances :

```bash
pip install streamlit openai
```

---

# 🔑 Configuration OpenAI

Ajoutez votre clé API en variable d’environnement :

### Windows

```bash
setx OPENAI_API_KEY "votre_cle_api"
```

### Mac / Linux

```bash
export OPENAI_API_KEY="votre_cle_api"
```

---

# 🚀 Lancement de l’Application

Dans le dossier racine :

```bash
streamlit run app.py
```

L’application sera accessible sur :

```
http://localhost:8501
```

---

# 🖥 Utilisation

1. Ouvrir l’application
2. Entrer le nom d’un employé absent
3. Cliquer sur "Trouver un remplaçant"
4. Lire l’explication générée

---

# 🧩 Choix Architecturaux

## Séparation stricte :

| Composant | Rôle        |
| --------- | ----------- |
| Python    | Décision    |
| LLM       | Explication |
| JSON      | Stockage    |
| Streamlit | Interface   |

---

## Pourquoi cette approche ?

* Fiabilité (la logique n’est pas déléguée à l’IA)
* Contrôle métier
* Transparence décisionnelle
* Prototype robuste en 9h

---

# 🔐 Limites Actuelles

* Pas de gestion complète des heures cumulées
* Pas d’optimisation avancée
* Données statiques
* Pas de base de données

---

# 🏁 Roadmap Possible

* Intégration base SQLite
* Gestion réelle des heures planifiées
* Optimisation automatique du planning
* Historique des décisions
* Dashboard KPI avancé

---

# 🏆 Positionnement Stratégique

Ce projet démontre :

* Compréhension métier pharmacie française
* Architecture IA propre
* Séparation décision / explication
* Approche pragmatique et démontrable

Ce n’est pas un chatbot générique.

C’est un agent métier spécialisé.

---

# 👤 Auteur

Wassim Gasmi
Projet démonstratif – Assistant RH IA
2026

---

