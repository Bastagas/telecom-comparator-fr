# PHASE 2 — Plan détaillé

> Document de cadrage de la Phase 2 du projet `telecom-comparator-fr`.
> Lu en complément de `PROJECT_BRIEF.md`.

---

## Vue d'ensemble

La Phase 2 transforme le **walking skeleton** (Phase 1, 1 opérateur) en un **outil de veille télécom complet** sur les 4 opérateurs FR, enrichi des données régulateur ARCEP. Elle est découpée en **3 sous-phases livrables indépendamment**, chacune apportant une valeur démontrable même si la suivante n'est pas atteinte.

```
Phase 2A — Extension multi-opérateurs (sans ARCEP)
   ↓
Phase 2B — Enrichissement ARCEP (couverture mobile + fibre par commune)
   ↓
Phase 2C — Polish & livrable final (radar, Docker, tests, README master)
```

**Règle d'or, héritée de la Phase 1** : sous-phase N+1 ne démarre que si N est complètement verte. Pas de chantiers parallèles à moitié finis.

---

## Phase 2A — Extension multi-opérateurs

### Scope

- 4 opérateurs FR scrapés en fibre (Free, Bouygues, SFR, Orange).
- Mobile reporté en Phase 2B (sera couplé à l'enrichissement ARCEP qui inclut couverture 4G/5G).
- Score composite calculé en Python (sans variable couverture pour l'instant — ajoutée en 2B).
- Refonte `results.php` : grille responsive, filtres avancés, pagination, tri.
- Endpoints API enrichis : `/api/operators`, filtres sur `/api/offers`, pagination.
- Historique des prix sur la fiche détail (table `prices_history` exploitée).
- Page `about.php` : méthodologie + sources.

### Tâches dans l'ordre

| # | Tâche | Livrable |
|---|---|---|
| **2A.0** | Scout des 3 sites (Bouygues, SFR, Orange) — 15 min, cartographie SSR/JS, anti-bot, structure des prix | Note dans le JOURNAL + ordre opérateurs validé |
| **2A.1** | Refacto scraper : `BaseScraper` abstraite, Free adapté, pattern multi-opérateurs | Module `scraper/operators/base.py` + free.py refait |
| **2A.2** | Module `scoring.py` + recalcul du score sur les offres existantes | `scraper/scoring.py` + score Free non-NULL |
| **2A.3** | Refonte `results.php` : grille responsive 1/2/3 colonnes selon viewport, filtres GET (operator, type, max_price, sort), pagination | results.php v2 |
| **2A.4** | Endpoints API enrichis : `/api/operators`, filtres + pagination sur `/api/offers` | api/app.py v2 |
| **2A.5** | Scraper opérateur #2 (selon résultats du scout) | Nouveau module |
| **2A.6** | Scraper opérateur #3 | Nouveau module |
| **2A.7** | Scraper opérateur #4 | Nouveau module |
| **2A.8** | Historique de prix : log automatique dans `prices_history` à chaque scrape + mini-graphique sur `offer.php` (Chart.js) | Update pipeline + offer.php |
| **2A.9** | `about.php` : méthodologie du score, sources, fréquence, disclaimer | Nouvelle page |
| **2A.10** | Polish + tag `v0.2.0a-phase2a` | Tag Git |

### Critères de done

- [ ] 4 opérateurs scrapés en fibre, au moins 1 offre par opérateur.
- [ ] Score composite calculé pour toutes les offres, valeur entre 0 et 10.
- [ ] `results.php` affiche 4+ cartes en grille, filtrage et tri opérationnels.
- [ ] `/api/offers?operator=free&max_price=40&sort=score` répond correctement.
- [ ] `offer.php` affiche un mini-graphique d'évolution de prix (au minimum 2 points).
- [ ] `about.php` documente la méthodologie de scoring.

---

## Formule du score composite (Phase 2A)

Score normalisé sur 10, arrondi à 1 décimale, calculé en Python (`scoring.py`).

| Variable | Poids | Calcul |
|---|---|---|
| Prix mensuel | **35%** | Min-max inversé sur le marché (prix le plus bas = 10) |
| Débit descendant | **25%** | Min-max sur le marché (5 Gbit/s = 10) |
| Options incluses | **15%** | Nombre × valeur catégorielle (streaming = 1, TV = 1, cloud = 0.5) |
| Engagement | **10%** | Sans engagement = 10, 12 mois = 5, 24 mois = 0 |
| Frais d'installation | **10%** | Min-max inversé (0€ = 10) |
| Bonus techno | **5%** | Wi-Fi 7 = +5, débit ↑ > 700 Mbps = +5, max 10 |

### Note importante

Cette formule sera **recalibrée en Phase 2B** quand la variable "qualité réseau ARCEP" sera ajoutée comme 7e variable. À ce moment-là, les 6 premières seront repondérées pour intégrer la nouvelle (probablement à 10-15%).

### Documentation utilisateur

`about.php` (Tâche 2A.9) doit expliciter cette formule en français accessible, avec un exemple concret.

---

## Phase 2B — Enrichissement ARCEP

### Scope

- Import du référentiel **communes INSEE** (~35 000 communes, seed CSV depuis data.gouv.fr).
- Import des données **ARCEP "Mon Réseau Mobile"** (couverture mobile par commune × opérateur).
- Import des données **ARCEP "Observatoire THD"** (couverture fibre par commune).
- **Ajout du mobile** au catalogue (forfaits mobiles des 4 opérateurs).
- Bloc "Couverture commune" sur `offer.php` (saisie code postal/commune → indicateurs).
- Endpoints `/api/coverage` et `/api/communes/search`.
- **Recalcul du score composite** avec 7e variable "qualité réseau".

### Pré-requis Phase 2A

Toute la 2A doit être verte. Pas négociable.

---

## Phase 2C — Polish & livrable final

### Scope

- **Composant radar** sur `offer.php` (Chart.js, offre vs moyenne marché — la maquette est déjà livrée).
- **Tests minimaux** : fixtures HTML par opérateur, tests unitaires des parseurs.
- **`docker-compose.yml`** : MySQL + phpMyAdmin + PHP + Flask, livraison reproductible.
- **README final** : pitch portfolio, architecture, captures d'écran, parcours d'évaluation pour le jury.
- **Tag `v0.2.0-phase2`**.

---

## Hors scope explicite (Phase 3 / post-master)

Documenté ici pour discipline mentale.

- Carte interactive Leaflet.
- Géocodage par adresse exacte (BAN).
- Recommandation contextuelle "moins cher dans cette commune".
- Comparaison côte à côte de 2 offres.
- Système d'auth, favoris, alertes prix.
