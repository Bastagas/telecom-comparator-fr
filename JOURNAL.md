# Journal de bord — Comparateur d'offres télécom FR

> Trace les décisions techniques, les obstacles, les apprentissages.
> Une entrée par tâche significative, datée, concise.

---

## Phase 1 — Walking skeleton

### 2026-04-26 — Tâche 1.2 — Scraper Free Pop

**Choix techniques**
- Extraction par regex sur HTML brut plutôt que sélecteurs CSS. Les classes Tailwind utility-first de free.fr (`text-16`, `mb-0`, suffixes hashés type `_blackBold__eTfyn`) sont trop volatiles pour bâtir un parser stable. On vise des signatures sémantiques (`Frais de mise en service NN€`, `jusqu'à N Gbit/s ... en descendant`).
- Pas de Playwright. La page `https://www.free.fr/freebox/freebox-pop/` est rendue côté serveur, `requests` suffit. UA navigateur classique, pas d'anti-bot rencontré.
- Upsert atomique via `INSERT ... ON DUPLICATE KEY UPDATE` adossé à la `UNIQUE KEY (operator_id, type, name)` ajoutée en amont sur `offers`.

**Données extraites pour Freebox Pop**
- Prix mensuel 39,99 € — promo 29,99 € pendant 12 mois.
- Sans engagement, frais de mise en service 49 €.
- Débits 5000 / 900 Mbps, FTTH, Wi-Fi 7.
- Score laissé à `NULL` (calcul prévu dans une tâche dédiée).

**Idempotence prouvée**
- Deux runs consécutifs → toujours 1 ligne en base.
- `first_seen_at` figé, `last_scraped_at` mis à jour au second run.

**Limitations connues**
- 1 seul opérateur (Free), 1 seule offre (Pop). La Phase 2 généralise aux 4 opérateurs et à toutes leurs offres fibre/mobile/bundle.
- Parser regex à durcir en Phase 2 (catalogue de fixtures HTML, tests unitaires, fallback agrégateur si Free change la mise en page).

### 2026-04-26 — Tâche 1.4 — API Flask

**Livré**
- 2 endpoints : `GET /api/offers` (liste, JOIN operators) et `GET /api/offers/<id>` (détail enrichi avec `pricing`, `specs.fibre`/`specs.mobile`, `options`, opérateur complet, 404 JSON sur id inconnu). Format aligné sur `00_brief/screens.md` Partie 2.

**Choix techniques**
- `api/db.py` distinct du scraper. L'API n'importe pas `scraper.*`. Découplage des couches : chaque module a ses deps minimales et peut être déployé indépendamment (Docker, prod).
- `.env` racine partagé scraper + API : credentials BDD identiques, pas de duplication. Port API exposé via `API_PORT` (12-factor).

**Gotcha macOS — port 5000 / AirPlay Receiver**
- Sur macOS Monterey+, `ControlCenter` (AirPlay Receiver) écoute en `*:5000` (IPv4 + IPv6) et capture les requêtes `localhost:5000` en répondant `403 AirTunes`.
- Bascule sur **port 5001** (paramétrable via `API_PORT` dans `.env`, défaut 5001). 3 curls validés sur `localhost:5001`.

**Limitations Phase 1**
- Pas de filtres (`operator`, `type`, `max_price`, `sort`), pas de pagination, pas d'endpoints `/api/operators`, `/api/coverage`, `/api/communes/search`. Tout cela en Phase 2.

### 2026-04-26 — Tâche 1.3 — Page PHP Direction C

**Livré**
- `web/results.php` (écran 2) qui consomme la BDD et rend la liste des offres avec la maquette Direction C : carte `.offer-card` avec head (kicker opérateur + acid-pill), nom, badges, bloc prix (promo + prix-barré + acid-pill côte à côte + fineprint), score, bouton primaire teal.
- 3 fichiers CSS séparés : `tokens.css` (palette, typo, espacements depuis TOKENS.md), `components.css` (offer-card, acid-pill, score-bar, btn-primary, badges), `layout.css` (page chrome, filtres, grille, animations d'entrée).
- 5 animations conformes à ANIMATIONS.md : #1/#3 pure CSS, #2/#4/#5 armées par `animations.js` via Intersection Observer.
- `index.php` placeholder (302 → results.php), à remplacer en Phase 2.

**Choix techniques**
- **PDO** plutôt que mysqli : interface standardisée, bindings préparés, pas de couplage MySQL spécifique. `db.php` expose `get_pdo()` (singleton, charset utf8mb4, ERRMODE_EXCEPTION).
- **Parser .env maison** (10 lignes) plutôt que `vlucas/phpdotenv` via Composer : aucune dep PHP nécessaire en Phase 1, MAMP exécute le PHP directement. Si on ajoute des libs PHP en Phase 2, on basculera sur Composer et ce parseur disparaîtra. Documenté dans le commentaire d'en-tête de `web/db.php`.
- **Symlink MAMP** (`htdocs/telecom → ~/dev/.../web`) : pas de déplacement du repo, pas de modification de la conf MAMP partagée. Documenté en README.
- **Hiérarchie BEM des sous-classes carte** (`offer-card__head`, `__name`, `__price`, `__score`, etc.) : décidée à l'implémentation faute de JSX livrés par Claude Design — à valider en revue design.

**Score NULL en Phase 1**
- Affichage : "—" en valeur, classe `.score-bar.is-empty` (fond gris uniforme), pas d'animation de fill (le JS ne déclenche le fill que si `data-score > 0`).

**Accessibilité — `prefers-reduced-motion`**
- Double garde : (a) media query CSS dans `layout.css` qui annule les transitions/keyframes, (b) branche dédiée dans `animations.js` qui rend tout en synchrone. Animations #1 et #3 (feedback essentiel hover/active) conservées comme recommandé par le designer.

**Limitations**
- 1 seule offre Phase 1, donc filtres testés en infra uniquement. Le tri "score DESC" met les NULL en queue (`ORDER BY (score IS NULL), score DESC`).
- Pas d'écran offer.php : le bouton "Voir le détail" pointera vers une 404 jusqu'à la Tâche 1.5 / Phase 2.

### 2026-04-26 — Tâche 1.5 — Pages PHP complètes (DERNIÈRE de la Phase 1)

**Livré**
- **Correction préalable** sur `results.php` : suppression de la pastille "Économisez X €/mois" du header de la carte (doublon avec celle près du prix barré). Remplacement par un type badge teal-bg (`Fibre`/`Mobile`/`Bundle`) qui équilibre le kicker opérateur.
- **3 partials PHP** (`web/partials/`) : `header.php` (chrome HTML, $pageTitle paramétrable), `footer.php` (page-footer + scripts + fermeture), `offer-card.php` (composant carte attendant `$offer` + `fmt_price`/`e`/`type_label` en scope). Refactor de `results.php` pour les utiliser, sans régression visuelle.
- **`index.php`** (vraie page d'accueil, remplace le 302) : hero avec `acid-kicker` "Mis à jour quotidiennement", H1 large, sous-titre. Form-first (select opérateur + segmented control type + input prix max + CTA "Rechercher" → redirige vers `results.php`). Section "Top offres du moment" (LIMIT 3 par score DESC) qui réutilise le partial offer-card.
- **`offer.php?id=X`** avec 3 cas couverts :
  - **200** : barre retour + référence `offer/<id>` mono, hero op-logo 56×56 (placeholder lettrine) + nom + badges, bloc prix volumineux, table specs 2 colonnes (débits, technologie, WiFi, TV, téléphone), bloc options (état vide explicite Phase 1), score + lien méthodologie, CTA externe `target=_blank rel=noopener noreferrer` vers `source_url`, encadré teal Phase 2 (historique + ARCEP + radar), mention dernière mise à jour.
  - **404** : id inconnu → page d'erreur sobre + CTA retour catalogue, header `HTTP 404`.
  - **400** : id absent ou non numérique (validé via `ctype_digit`) → message explicite + exemple, header `HTTP 400`.

**Choix techniques**
- Partials PHP plutôt qu'un mini-moteur de templates ou Twig : pas de Composer en Phase 1, le pattern `require` natif suffit pour 3 fichiers réutilisés.
- CSS éclaté : ajouts pour partials (page-footer__col/__link) et nouveaux composants (`acid-kicker`, `segmented`, `op-logo`, `specs`, `options-empty`, `phase2-placeholder`, `detail-*`, `error-page`, `btn-ghost`) commités au plus près de leur consommateur (commit c = index, commit d = offer).
- Page d'erreur partagée via la helper `render_error(int, string, string)` dans `offer.php`, qui inclut header/footer et `exit` proprement après le rendu.

**Phase 1 — verte ✅**

Le walking skeleton est maintenant complet de bout en bout :
- **BDD MySQL** (10 tables, 4 opérateurs + 9 options seedés).
- **Scraper Python** (Free Freebox Pop, idempotent, upsert atomique).
- **API Flask** (2 endpoints : liste + détail avec 404, port configurable).
- **Front PHP** (3 pages : accueil, résultats filtrables, détail avec 404/400).

Pipeline démontrable bout en bout sur 1 cas concret. La Phase 2 ouvre sur l'extension à 4 opérateurs, l'enrichissement ARCEP par commune, les filtres avancés / pagination / endpoints couverture, et l'historique des prix.
