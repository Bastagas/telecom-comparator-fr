# User Stories — Comparateur d'offres télécom FR

> **Format** : `En tant que [rôle], je veux [action], afin de [bénéfice]`
> **AC** = Acceptance Criteria
> **Phase** : 1 (walking skeleton) / 2 (master complet) / 3 (post-master, carte)

---

## US-1 : Recherche d'offres par opérateur (dropdown obligatoire) — Phase 1

**En tant que** visiteur,
**je veux** sélectionner un opérateur dans une liste déroulante,
**afin de** voir uniquement les offres de cet opérateur.

**AC**
- Page d'accueil avec balise `<select>` listant les 4 opérateurs + option "Tous".
- Au submit, l'utilisateur arrive sur une page listant les offres filtrées.
- Chaque résultat affiche : nom, prix mensuel, type, score.
- État vide si aucun résultat.

---

## US-2 : Filtrage par budget et type d'offre — Phase 1

**En tant que** visiteur recherchant un forfait,
**je veux** filtrer par type (fibre / mobile / bundle) et prix max,
**afin d'**identifier rapidement celles qui correspondent à mon budget.

**AC**
- Champs : type (radio ou select), prix max (input numérique).
- Tri par défaut : score décroissant.
- Possibilité de re-trier par prix.

---

## US-3 : Consultation de la fiche détaillée d'une offre — Phase 1

**En tant que** visiteur,
**je veux** cliquer sur une offre pour voir tous ses détails,
**afin de** comprendre exactement ce qu'elle inclut.

**AC**
- Page dédiée `offer.php?id=X`.
- Affiche : opérateur, nom, prix, engagement, frais, specs techniques, options incluses.
- Lien "Voir l'offre originale" vers la `source_url`.
- Date du dernier scraping affichée.

---

## US-4 : Évolution du prix dans le temps — Phase 2

**En tant que** visiteur intéressé par une offre,
**je veux** voir comment son prix a évolué,
**afin de** détecter une tendance avant de souscrire.

**AC**
- Sur la page détail, mini-graphique ou tableau des relevés de prix.
- Si moins de 2 relevés : "Historique en cours de constitution".

---

## US-5 : Accès programmatique aux données via API REST — Phase 1 (basique) puis Phase 2 (complet)

**En tant que** développeur tiers,
**je veux** interroger les offres via une API JSON,
**afin d'**intégrer les données ailleurs.

**AC Phase 1**
- `GET /api/offers` : liste basique.
- `GET /api/offers/<id>` : détail.

**AC Phase 2**
- Filtres query params (`operator`, `type`, `max_price`, `sort`).
- Pagination (`page`, `per_page`).
- `GET /api/operators`.
- Codes HTTP cohérents (200, 404, 400).
- Doc minimale dans le README (exemples `curl`).

---

## US-6 : Qualité réseau dans une commune (NOUVELLE) — Phase 2

**En tant que** visiteur regardant une offre,
**je veux** saisir un code postal ou un nom de commune,
**afin de** voir la couverture mobile et fibre de l'opérateur dans cette zone avant de souscrire.

**AC**
- Champ de saisie sur la page détail offre : code postal ou nom de commune (autocomplete).
- Le système géolocalise à la commune INSEE (pas à l'adresse exacte — voir disclaimer).
- Affichage des indicateurs ARCEP pour cet opérateur dans cette commune :
  - Mobile : 4G oui/non, 5G oui/non, 5G 3.5 GHz oui/non, qualité estimée
  - Fibre : % de locaux raccordables, nombre de locaux concernés
- Date des données ARCEP affichée (transparence sur la fraîcheur).
- Disclaimer : "Données régulateur à la maille commune. Pour une éligibilité fibre par adresse exacte, consultez le testeur de l'opérateur."

---

## US-7 : Endpoint API couverture (NOUVELLE) — Phase 2

**En tant que** développeur tiers,
**je veux** interroger les données de couverture par commune,
**afin de** consommer les données ARCEP enrichies.

**AC**
- `GET /api/coverage?code_insee=XXXXX&operator=Y` : couverture mobile + fibre pour la combinaison.
- `GET /api/communes/search?q=Montpellier` : autocomplete de communes.

---

## Phase 3 backlog (post-master, valorisation portfolio)

> Ces stories ne sont **pas dans le scope du rendu master**. Elles définissent l'horizon de la version cartographique.

### US-P3-1 : Carte interactive multi-couches
**En tant que** visiteur,
**je veux** voir sur une carte de France les zones de couverture par opérateur,
**afin de** comparer visuellement la couverture territoriale.

### US-P3-2 : Géocodage par adresse exacte
**En tant que** visiteur,
**je veux** saisir mon adresse complète,
**afin que** le système retrouve ma commune et me propose les meilleures offres pour ma zone.

### US-P3-3 : Recommandation contextuelle
**En tant que** visiteur,
**je veux** voir l'offre la moins chère ET avec la meilleure couverture pour ma commune,
**afin de** prendre une décision éclairée localement.

### US-P3-4 : Comparaison côte à côte de 2 offres
**En tant que** visiteur,
**je veux** sélectionner 2 offres et les voir côte à côte,
**afin de** comparer ligne à ligne.

---

## Out of scope (toutes phases confondues)

- Création de compte / favoris / alertes (nécessiterait auth + back office).
- Souscription en ligne (relais vers le site opérateur uniquement).
- Données ARCEP en temps réel (publications trimestrielles, pas live).
