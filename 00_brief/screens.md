# Écrans & Endpoints — Comparateur d'offres télécom FR

> Document destiné à **Claude Design** (maquettes UX/UI) et **Claude Code** (implémentation).
> **Version 2** : ajout du bloc couverture ARCEP sur la fiche détail.

---

## Partie 1 — Écrans web (PHP)

### Écran 1 — Accueil / Recherche — Phase 1
**Fichier cible** : `index.php`
**User stories couvertes** : US-1, US-2

**Éléments UI**
- Hero / titre du projet + baseline ("Comparez les offres télécom FR mises à jour quotidiennement, enrichies des données régulateur ARCEP").
- Formulaire de recherche :
  - `<select>` opérateur (Tous / Orange / SFR / Bouygues / Free)
  - `<select>` ou radio : type d'offre (Tous / Fibre / Mobile / Bundle)
  - Input numérique : prix max (€/mois)
  - Bouton "Rechercher"
- Section "Top 5 offres du moment" (tri par score).
- Footer : lien "Méthodologie du score", "API documentation", date de dernière mise à jour, mention sources (opérateurs + ARCEP).

**Données nécessaires** : `operators`, top 5 `offers` joint avec `operators`.

---

### Écran 2 — Liste des résultats — Phase 1
**Fichier cible** : `results.php`
**User stories couvertes** : US-1, US-2

**Éléments UI**
- Rappel des filtres appliqués en haut, modifiables.
- Cartes "offre" :
  - Logo opérateur
  - Nom de l'offre
  - Prix mensuel (avec promo en évidence si applicable)
  - Badges : type, 5G/FTTH, engagement
  - Score visuel (étoiles ou jauge /10)
  - Bouton "Voir le détail"
- Tri : score (défaut) / prix croissant / prix décroissant.
- Pagination si > 20 résultats.
- État vide.

**Données** : `offers` JOIN `operators` + jointures conditionnelles `fibre_specs`/`mobile_specs`.

---

### Écran 3 — Détail d'une offre — Phase 1 (base) puis Phase 2 (enrichi)
**Fichier cible** : `offer.php?id=X`
**User stories couvertes** : US-3, US-4, US-6

**Éléments UI Phase 1**
- En-tête : logo opérateur + nom de l'offre + retour.
- Bloc prix : mensuel, promo, engagement, frais.
- Bloc spécifications techniques (varie selon type) :
  - Fibre : débits, techno, WiFi, TV
  - Mobile : data FR/EU, 5G, appels/SMS
- Bloc options : icônes, distinction inclus / payant.
- Footer : score expliqué + lien "Voir sur le site de [opérateur]".
- Mention "Dernière mise à jour : [last_scraped_at]".

**Éléments UI ajoutés en Phase 2**
- **Bloc historique de prix** (US-4) : graphique linéaire ou tableau (Chart.js).
- **Bloc "Couverture dans votre commune"** (US-6) :
  - Champ de saisie code postal / nom de commune avec autocomplete.
  - Au submit, affichage côte à côte :
    - Mobile : icônes 4G / 5G / 5G 3.5 GHz avec qualité (vert/orange/rouge)
    - Fibre : pourcentage de locaux raccordables + nombre absolu
  - Date des données ARCEP en petit.
  - Disclaimer "Données à la maille commune. Pour l'éligibilité par adresse exacte, voir le site de l'opérateur."

**Données** : `offers` + `fibre_specs`/`mobile_specs` + `offer_options` JOIN `options` + `prices_history` + `coverage_mobile`/`coverage_fibre` + `communes`.

---

### Écran 4 (bonus) — Méthodologie & À propos — Phase 2
**Fichier cible** : `about.php`

**Éléments UI**
- Explication du calcul du score composite (pondérations prix/débit/options/couverture).
- Sources des données : URLs des opérateurs + référence ARCEP.
- Fréquence de mise à jour (scraping quotidien, ARCEP trimestriel).
- Mentions légales / disclaimer.

---

### Écran 5 (Phase 3 — out of scope master) — Carte interactive
**Fichier cible** : `map.php` (à créer post-master)

**Hors scope du rendu master.** Documenté ici pour mémoire.
- Leaflet.js + tuiles OpenStreetMap.
- Couches commutables : couverture 4G, 5G, 5G 3.5 GHz, fibre — par opérateur.
- Au clic sur une commune : popup avec offres recommandées + couverture.
- Champ "Tester mon adresse" via API Adresse BAN.

---

## Partie 2 — Endpoints API (Flask)

> Base URL en dev : `http://localhost:5000/api`

### Phase 1 (basique)

**`GET /api/offers`** — liste simple, sans filtres avancés.
**`GET /api/offers/<id>`** — détail avec specs et options.

### Phase 2 (complet)

**`GET /api/operators`**
```json
[{"id": 1, "name": "Orange", "slug": "orange", "website_url": "..."}]
```

**`GET /api/offers`** — avec filtres et pagination.
- Query params : `operator`, `type`, `max_price`, `sort` (`score`|`price_asc`|`price_desc`), `page`, `per_page`.
```json
{
  "data": [
    {"id": 12, "operator": "Free", "type": "fibre", "name": "Freebox Pop", "monthly_price": 39.99, "score": 8.5}
  ],
  "pagination": {"page": 1, "per_page": 20, "total": 47}
}
```

**`GET /api/offers/<id>`** — détail enrichi avec historique prix.
```json
{
  "id": 12,
  "operator": {...},
  "type": "fibre",
  "name": "Freebox Pop",
  "pricing": {"monthly": 39.99, "promo": null, "commitment_months": 0},
  "specs": {"download_mbps": 5000, "upload_mbps": 700, "technology": "FTTH"},
  "options": [{"name": "Disney+", "is_included": true}],
  "price_history": [{"price": 39.99, "captured_at": "..."}]
}
```

**`GET /api/coverage`** (US-7) — couverture par commune et opérateur.
- Query params : `code_insee` (requis), `operator` (slug, optionnel pour tous opérateurs).
```json
{
  "commune": {"code_insee": "75056", "name": "Paris", "department": "75"},
  "operator": "free",
  "mobile": {"has_4g": true, "has_5g": true, "has_5g_3500mhz": true, "quality_4g": "very_good", "quality_5g": "good"},
  "fibre": {"pct_couverture": 98.5, "locaux_raccordables": 1250000, "locaux_total": 1268000},
  "data_source_mobile": "ARCEP MRM 2025-Q4",
  "data_source_fibre": "ARCEP THD 2025-Q4"
}
```

**`GET /api/communes/search?q=Montp`** — autocomplete pour le champ commune.
```json
[
  {"code_insee": "34172", "name": "Montpellier", "postal_code": "34000"}
]
```

Tous les endpoints renvoient des codes HTTP cohérents : 200, 404 (id ou code INSEE inconnu), 400 (params invalides).

---

## Partie 3 — Brief design (à passer à Claude Design)

Pour un rendu cohérent avec un positionnement "outil de veille télécom pro" :

- **Palette** : neutre + 1 accent (bleu froid type "data dashboard"), **pas** les couleurs marketing des opérateurs.
- **Typo** : sans-serif moderne (Inter, IBM Plex Sans).
- **Composants clés à designer** :
  - Carte d'offre (utilisée écran 2)
  - Badges (technologie, 5G, engagement)
  - Score visuel (étoiles ou jauge)
  - Tableau de specs
  - Mini-graphique d'évolution de prix (Phase 2)
  - **Bloc couverture commune** : icônes 4G/5G/fibre avec indicateurs colorés (Phase 2)
  - Footer commun
- **Responsive** : mobile-first (les recruteurs testent sur mobile).
- **Accessibilité** : contraste AA, labels sur les selects, focus states visibles.
- **Densité d'information** : assumer la verticalité, ne pas sur-aérer — c'est un outil pro, pas un site de marque.
