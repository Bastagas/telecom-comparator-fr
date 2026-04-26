# PROJECT BRIEF — Comparateur d'offres télécom FR

> **Document chapeau du projet.** À coller en début de session Claude Code et Claude Design pour briefer en 1 minute.

---

## 1. Vue d'ensemble

**Nom de travail** : `telecom-comparator-fr`
**Pitch en une phrase** : Outil de veille qui agrège les offres commerciales des 4 opérateurs télécom français (Orange, SFR, Bouygues, Free) et les enrichit avec les données du régulateur ARCEP pour produire un score qualité/prix défendable.

**Double finalité**
- **Académique** : projet de master couvrant scraping Python + BDD MySQL + PHP + API Flask.
- **Portfolio** : démontre une compétence de bout en bout (data ingestion → modélisation → exposition) sur un domaine métier (télécom FR) cohérent avec le profil consultant IDATE.

---

## 2. Architecture en 3 phases

| Phase | Périmètre | Statut | Critère de réussite |
|---|---|---|---|
| **1 — Walking skeleton** | 1 opérateur (Free) scrapé + BDD + 1 page PHP + 1 endpoint API | À démarrer | Pipeline complet bout en bout, même rudimentaire |
| **2 — Brief master complet** | 4 opérateurs + enrichissement ARCEP commune-level + toutes les pages + API documentée | Backlog | Couvre l'intégralité du brief de cours, livrable noté |
| **3 — Carte interactive** | Leaflet + géocodage BAN + croisement couverture/prix par commune | Hors scope master, post-rendu | Killer feature portfolio |

**Règle d'or** : Phase N+1 ne démarre que si Phase N est complètement verte.

---

## 3. Stack technique

| Couche | Techno | Justification |
|---|---|---|
| BDD | MySQL 8 + phpMyAdmin | Brief impose, MAMP fournit |
| Stack locale | MAMP | Le plus rapide à déployer sur Mac |
| Stack livraison | `docker-compose` (MySQL + phpMyAdmin + PHP + Flask) | Reproductibilité jury + portfolio |
| Scraping | Python + BeautifulSoup (sites statiques) / Playwright (sites JS-heavy) | À évaluer site par site |
| Connecteur DB Python | `mysql-connector-python` | Officiel Oracle, stable |
| Front public | PHP 8 (sans framework) | Brief impose |
| API | Flask + Flask-RESTful | Brief impose Flask |
| Front carte (Phase 3) | Leaflet.js + tuiles OpenStreetMap | Open source, pas de clé API |
| Géocodage (Phase 3) | API Adresse BAN (api-adresse.data.gouv.fr) | Gratuit, gouvernemental, pas d'auth |

---

## 4. Sources de données

### Scraping (source primaire — Phase 1 & 2)
- Pages tarifaires officielles des 4 opérateurs
- Fallback / agrégateur si bloqué : Ariase, Selectra
- Fréquence cible : quotidienne (cron)

### APIs / Open Data (enrichissement — Phase 2)
- **ARCEP** — `data.arcep.fr`
  - "Mon Réseau Mobile" : couverture 4G/5G par commune × opérateur
  - "Observatoire du Très Haut Débit" : couverture fibre par commune
  - Fréquence de publication : trimestrielle
- **ANFR** *(optionnel Phase 2, plus probable Phase 3)* — `data.anfr.fr`
  - Sites mobiles autorisés et déployés par opérateur, bande, technologie

### APIs (Phase 3 uniquement)
- **API Adresse BAN** — géocodage adresse → coordonnées + code INSEE

---

## 5. Arborescence du repo

```
telecom-comparator-fr/
├── 00_brief/                  # Documents de cadrage (ce dossier)
│   ├── PROJECT_BRIEF.md       # ← tu es ici
│   ├── data_model.sql
│   ├── user_stories.md
│   └── screens.md
├── db/
│   ├── schema.sql             # copie versionnée du data_model
│   └── seeds/                 # données de référence (communes INSEE, etc.)
├── scraper/
│   ├── operators/             # un module par opérateur
│   │   ├── free.py
│   │   ├── orange.py
│   │   └── ...
│   ├── enrichers/             # ARCEP, ANFR
│   ├── pipeline.py            # orchestrateur
│   └── requirements.txt
├── api/                       # Flask
│   ├── app.py
│   ├── routes/
│   └── requirements.txt
├── web/                       # PHP
│   ├── index.php
│   ├── results.php
│   ├── offer.php
│   ├── about.php
│   └── assets/
├── docker/                    # Phase 2+
│   └── docker-compose.yml
└── README.md
```

---

## 6. Conventions

- **Naming BDD** : `snake_case` partout, tables au pluriel, FK en `<table>_id`.
- **Naming Python** : `snake_case`, modules courts.
- **Naming PHP** : `snake_case` pour les fichiers, `camelCase` pour les variables.
- **Commits** : style conventionnel (`feat:`, `fix:`, `docs:`, `refactor:`).
- **Branches** : `phase-1/walking-skeleton`, `phase-2/arcep-integration`, etc.
- **Charset** : UTF-8 mb4 en BDD, UTF-8 partout ailleurs.

---

## 7. Comment briefer chaque Claude

### Claude Code (VS Code)
> *"Lis tous les fichiers de `00_brief/`. Tu travailles actuellement sur la Phase [N]. Voici la tâche : [tâche précise]. Respecte l'arborescence définie."*

### Claude Design
> *"Lis `00_brief/PROJECT_BRIEF.md` et `00_brief/screens.md`. Propose-moi des [wireframes / maquettes hi-fi] pour [écran spécifique]. Respecte le brief design en fin de `screens.md`."*

---

## 8. Risques identifiés

- **Sites opérateurs anti-bot** : prévoir un fallback Playwright + headers réalistes. En dernier recours, scraper un agrégateur.
- **Données ARCEP en retard** : la dernière publication peut dater de plusieurs mois. Toujours afficher la date de capture.
- **Scope creep Phase 3** : tentation forte de coder la carte avant la Phase 2. **Discipline impérative.**
- **Mentions légales** : ajouter un disclaimer sur chaque page ("Données informatives, non contractuelles, vérifier sur le site officiel avant souscription").
