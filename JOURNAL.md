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
