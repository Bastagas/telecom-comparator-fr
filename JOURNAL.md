# Journal de bord — Comparateur d'offres télécom FR

> Trace les décisions techniques, les obstacles, les apprentissages.
> Une entrée par tâche significative, datée, concise.

---

## Phase 2A — Extension multi-opérateurs

### 2026-04-26 — Tâche 2A.0 — Scout sites opérateurs

**Objectif** — cartographier en 15 min la difficulté des 3 prochaines cibles (Bouygues, SFR, Orange) avant de figer l'ordre d'attaque et de concevoir le `BaseScraper`.

**Méthode** — `requests` + UA Chrome 124 + `Accept-Language: fr-FR`. Mesure HTTP, taille, occurrences `€` / `/mois`, présence d'anti-bot, structure (JSON-LD, microdata, inline JSON, Tailwind).

**Résultats**

| Opérateur | URL | HTTP | Taille | Prix visibles | Anti-bot | Structure | Difficulté |
|---|---|---|---|---|---|---|---|
| Free *(rappel Phase 1)* | free.fr/freebox/freebox-pop/ | 200 | 169 KB | oui | non | Tailwind brut, classes hashées | Facile (regex) |
| **Bouygues** | bouyguestelecom.fr/offres-internet | 200 | **508 KB** | oui (256 `/mois`) | non | **JSON-LD** + Tailwind | Facile |
| **SFR** | sfr.fr/offre-internet/ | 200 | 162 KB | oui (37 `/mois`) | non | **JSON-LD** | Facile |
| **Orange** | boutique.orange.fr/internet/offres-fibre | 200 | 160 KB | oui (43 `/mois`) | non | **Microdata** (`itemscope`) | Facile |

**Note URL Orange** — `nouveau.orange.fr/offres/internet/` (URL initiale du brief) ne résout plus en DNS. Le portail `www.orange.fr` est un SPA qui ne sert qu'un shell de 1,1 KB. Le bon point d'entrée pour scraper est `boutique.orange.fr/internet/offres-fibre` (SSR, prix visibles, "Livebox" cité 325 fois). À refléter dans le scraper Phase 2A.7.

**Constats globaux**
- Aucun des 3 sites n'oppose d'anti-bot (Cloudflare, DataDome, hCaptcha) à un GET simple avec UA navigateur.
- Tous les 3 sont en SSR avec prix visibles dans le HTML brut → pas besoin de Playwright.
- 2 sur 3 (Bouygues, SFR) exposent du JSON-LD, plus stable que des sélecteurs CSS Tailwind. À privilégier dans le parsing.
- Orange utilise des microdata `itemprop`/`itemscope` — exploitables proprement avec BeautifulSoup.

**Stratégie par opérateur**
- **Bouygues** — Approche identique Free, mais on extrait via JSON-LD en priorité (`script[type="application/ld+json"]`). Regex en filet de sécurité.
- **SFR** — Idem. JSON-LD prioritaire.
- **Orange** — BeautifulSoup sur les microdata `itemscope/itemprop`. Pas de JSON-LD.

**Ordre d'attaque recommandé** (Phase 2A.5 → 2A.7)
1. **SFR** — petit volume + JSON-LD standard, valide la classe `BaseScraper` sur un cas simple.
2. **Bouygues** — JSON-LD aussi (acquis SFR réutilisable), volume plus gros confirme la robustesse.
3. **Orange** — microdata, approche complémentaire, ferme le cycle des 3 patterns d'extraction.

Pas de "fallback agrégateur" (Selectra/Ariase) nécessaire en Phase 1 du scout. À garder en réserve si un site bascule sur du JS-only.

### 2026-04-26 — Tâche 2A.1 — Refacto BaseScraper

**Objectif** — sortir Free de son fichier procédural pour préparer SFR/Bouygues/Orange en sous-classes propres.

**Choix architectural validé pendant le scout**
- Le scout a révélé 3 patterns d'extraction distincts (Tailwind/regex pour Free, JSON-LD pour SFR/Bouygues, microdata pour Orange).
- BaseScraper expose donc le **squelette uniquement** (fetch HTTP par défaut, orchestration, upsert, gestion d'erreurs) et **n'impose aucune méthode de parsing** : `parse_offers(html) -> list[dict]` est laissé abstrait, libre à chaque sous-classe.
- Free reste sur son extraction regex actuelle. Le code de parsing est strictement déplacé (pas de réécriture).

**Contrat de dict pour upsert_offer** — documenté dans la docstring de `scraper/operators/base.py` :
```
{
  operator_slug, type, name, monthly_price, promo_price,
  promo_duration_months, commitment_months, setup_fee,
  source_url, score,
  fibre_specs: {download_mbps, upload_mbps, technology, wifi_standard,
                has_tv, tv_channels_count, has_landline} | None
}
```
`upsert_offer` accepte ce dict unique au lieu de l'ancienne signature `(slug, offer, fibre_specs)`. Aucun wrapper de compat conservé : on est seul consommateur.

**Gestion d'erreur** — `BaseScraper.run()` enveloppe fetch + parse + upsert dans des try/except et logge les exceptions. Un opérateur qui échoue retourne 0 offre upsertée mais ne casse pas l'itération sur les autres opérateurs dans `pipeline.py`.

**Pipeline** — `OPERATORS: list[type[BaseScraper]] = [FreeScraper]` (extensible 2A.5/6/7 par simple `import` + `append`). Code de retour = nombre d'opérateurs sans aucune offre upsertée (0 = green).

**Vérif idempotence + non-régression**
- Avant refacto : 1 ligne Free, prix 39,99/29,99 €, 5000/900 Mbps, FTTH Wi-Fi 7.
- Après refacto + 1 run pipeline : strictement identique (même `id=1`, même prix, mêmes débits).
- `last_scraped_at` mis à jour, `first_seen_at` figé : la UNIQUE KEY fait toujours son travail.

### 2026-04-26 — Tâche 2A.2 — Scoring composite

**Objectif** — calculer un score /10 par offre, persisté en BDD, affiché en front.

**Formule** (cf. `00_brief/PHASE_2_PLAN.md` pour la version chapeau)
| Variable | Poids | Sens | Calcul |
|---|---|---|---|
| Prix mensuel | 35% | inversé | min-max sur le marché |
| Débit descendant | 25% | direct | min-max sur le marché |
| Options incluses | 15% | direct | Σ poids catégories × 2, capé à 10 |
| Engagement | 10% | inversé | 0 mois = 10, 24 mois = 0, linéaire |
| Frais d'installation | 10% | inversé | min-max sur le marché |
| Bonus techno | 5% | seuils | Wi-Fi 7 = +5, débit ↑ ≥ 700 = +5 |

Catégories d'options pondérées : streaming = 1, tv = 1, storage = 0.5, gaming = 0.5, other = 0.5. Score d'option = Σ × 2, capé à 10.

**Cas limite — `min == max` sur le marché → 7.5 par défaut**
- Quand une variable n'a aucune dispersion (typique : un seul opérateur en BDD au début de la 2A), `_normalize` renvoie `NEUTRAL_FALLBACK = 7.5`.
- Justification : valeur "marché de référence neutre", évite que le score ne saute brutalement quand on passe de 1 à 2 offres avec un prix plus haut. La barre teal s'affiche correctement (≠ vide) pendant toute la transition multi-opérateurs Phase 2A.

**Architecture**
- `compute_score(offer, market)` est une fonction pure : la pondération des options est pré-calculée côté SQL via un `CASE` par catégorie, agrégé en `options_weighted` dans la même requête.
- `recalculate_all_scores(conn)` est appelé **une seule fois** à la fin du pipeline, après l'itération sur tous les opérateurs : les stats de marché dépendent de l'ensemble des offres, donc impossible à calculer offre par offre dans `BaseScraper.run`.

**Score Freebox Pop seule en BDD = 6.8 / 10**
Détail :
- price (39.99, min=max → 7.5) × 0.35 = 2.625
- download (5000, min=max → 7.5) × 0.25 = 1.875
- options (0 incluses) × 0.15 = 0
- engagement (sans engagement → 10) × 0.10 = 1.0
- setup (49 €, min=max → 7.5) × 0.10 = 0.75
- tech_bonus (Wi-Fi 7 +5, upload 900 ≥ 700 +5 → 10) × 0.05 = 0.5
- **Total = 6.75 → arrondi 6.8**

**Front**
- `results.php` affiche désormais "6,8 / 10" et la barre teal se remplit à 68% au mount de la carte (animation `score-bar > .fill` activée par `animations.js`, déjà en place depuis Phase 1).

**Recalibrage prévu en Phase 2B**
- Ajout d'une 7e variable "qualité réseau ARCEP" — les 6 poids actuels seront repondérés pour intégrer la nouvelle (probablement 10–15 %).

### 2026-04-26 — Tâche 2A.5 — Scraper SFR

**Note inversée du scout** — le scout 2A.0 avait noté "JSON-LD présent" sur SFR. En réalité le seul `<script type="application/ld+json">` de la page est un `BreadcrumbList` (fil d'Ariane), inutilisable pour les produits. Stratégie revue à l'inspection rapprochée : extraction des **mentions légales** (HTML stable car cadre légal) pour le prix + engagement + nom, complété par un **mapping documenté Box → débits/Wi-Fi** dérivé des paragraphes "débit théorique" du même HTML.

**Périmètre Phase 2A — 2 offres scrapées sur 4 détectées**
- ✅ **SFR Fibre Premium** — 45,99 €, sans engagement, Box 10+, FTTH 8 Gb/s symétrique, Wi-Fi 7.
- ✅ **SFR Fibre Power** — 36,99 €, engagement 12 mois, Box 8, FTTH 1 Gb/s↓ / 100 Mbps↑, Wi-Fi 6.
- ⚠️ **SFR Starter** (Box 7) et **SFR Power S** (Box 8) — *skippées avec warning*. Leurs débits sont formulés en fourchettes ambiguës dans le HTML (« 500 Mb/s ou 1 Gb/s »), le brief impose de ne pas insérer une ligne avec `download_mbps = NULL`. À reprendre Phase 2C avec fixtures HTML.

**Mapping Box → fibre_specs** (constante `KNOWN_OFFERS` dans `sfr.py`, annotée `# vérifié 2026-04-26`) :
| Box | Download | Upload | Wi-Fi |
|---|---|---|---|
| Box 10+ (Premium) | 8000 Mbps | 8000 Mbps | Wi-Fi 7 |
| Box 8 (Power) | 1000 Mbps | 100 Mbps | Wi-Fi 6 |

`setup_fee = 49 €` (constante observée "Frais d'ouverture de service de 49€ sur les offres Box").

**Impact sur le score Free — preuve que le min-max est sain**
- **Avant SFR** (Free seul, min == max sur tout) : score 6.8 (porté par les fallbacks 7.5).
- **Après SFR** (3 offres, vrai marché) : score **6.0** (-0.8). Le min-max n'est plus dégénéré : Free reste le mieux placé du panel (Wi-Fi 7 + sans engagement + débit honnête + prix médian), mais perd les fallbacks neutres.
- Scores SFR : Premium 4.8, Power 4.8 (égalité mathématique fortuite — Premium domine sur débit/Wi-Fi 7, Power sur prix, ça compense).

**Limitations connues**
- 2 offres SFR sur 4 (couverture 50% du catalogue commercial fibre). Le brief privilégie qualité > quantité.
- Pas de promo extraite (la page affiche un "29,99€ Sans engagement" en hero, mais sans rattachement explicite à une offre nommée — non scrapable proprement sans BS4 + sélecteur précis, reporté Phase 2C).
- Mapping Box → débits codé en dur. Les fixtures HTML versionnées et tests unitaires (Phase 2C) sécuriseront ce point.

**Dette technique identifiée** — KNOWN_OFFERS hardcode les débits. À remplacer par un parsing dynamique du HTML en Phase 2C.

**Observation calibrage** — SFR Power et Premium ont le même score (formule équilibrant prix bas/débit faible vs prix haut/débit élevé). Recalibrage prévu Phase 2B avec ajout de la 7e variable ARCEP.

### 2026-04-26 — Tâche 2A.6 — Scraper Bouygues

**Stratégie d'extraction validée** — Bouygues n'expose pas de JSON-LD Product (uniquement un BreadcrumbList comme SFR) ni de microdata. **Mais** un script Next.js inline (~178 KB, identifié par la cooccurrence des champs `downRates` et `rangeNg`) contient un **store complet** des offres FAI avec tous les champs structurés requis : `name`, `categories`, `technology`, `downRates`, `upRates`, `details.price.{initial, forever, final}`, `discounts[].duration`, `obligation`, `obligationLabel`. Extraction **100 % dynamique, zéro hardcoding** — vrai progrès vs SFR.

**3 offres Bouygues fibre upsertées**
| Offre | `monthly_price` | `promo_price` (durée) | Engagement | ↓ / ↑ Mbps | Wi-Fi |
|---|:-:|:-:|:-:|:-:|:-:|
| Bbox Fit | 34,99 € | 27,99 € (12 mois) | 12 mois | 1000 / 700 | Wi-Fi 6 |
| Bbox Must | 40,99 € | 33,99 € (12 mois) | 12 mois | 2000 / 900 | Wi-Fi 7 |
| Bbox Ultym | 49,99 € | 42,99 € (12 mois) | 12 mois | 8000 / 8000 | Wi-Fi 7 |

Variantes Banque, Gaming, Smart TV et box 4G/5G **exclues** (bundles spécialisés hors comparateur fibre core). Le store contient des doublons (même offre référencée sous plusieurs onglets) : dédup par nom avec préférence "sans engagement" si dispo, sinon engagement le plus court — règle non déclenchée ici car les 3 Bbox principales sont toutes en `monthly12` sans alternative `none`.

**Impact sur les scores du panel (3 opérateurs, 6 offres)**
| Offre | Avant Bouygues | Après Bouygues | Δ |
|---|:-:|:-:|:-:|
| Free Pop | 6.0 | **5.3** | -0.7 |
| SFR Fibre Premium | 4.8 | **4.9** | +0.1 |
| SFR Fibre Power | 4.8 | **3.5** | -1.3 |
| Bbox Fit | — | **5.2** | nouveau |
| Bbox Must | — | **4.5** | nouveau |
| Bbox Ultym | — | **4.5** | nouveau |

Free reste 1er du panel (sans engagement + Wi-Fi 7 + débit honnête + prix médian). Bbox Fit prend la 2e place grâce au prix le plus bas du panel — le score reflète le compromis "petit débit mais pas cher". SFR Power chute à 3.5 (engagement 12 mois + débit faible + pas de Wi-Fi 7 = pénalité multiple).

**Dette technique identifiée — `setup_fee_waived` (Phase 2C)**
Le `setup_fee` est fixé à 48 € pour les Bbox FTTH (tarif officiel) même si la promo en cours offre les frais de mise en service. Le schéma BDD actuel ne distingue pas tarif officiel vs offre commerciale. **À résoudre en Phase 2C** : ajouter une colonne `setup_fee_waived BOOLEAN DEFAULT FALSE` (ou `setup_fee_promo DECIMAL(6,2) NULL`) dans la table `offers`, avec mise à jour du scraper Bouygues pour la peupler depuis la liste des promos détectées dans le store Next.js.

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
