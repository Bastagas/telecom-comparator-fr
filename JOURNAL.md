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
