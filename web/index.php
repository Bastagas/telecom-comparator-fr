<?php
/**
 * Écran 1 — index.php
 * Page d'accueil : hero + form-first + Top offres du moment.
 * Cf. 00_brief/screens.md écran 1 et 00_brief/dc/Hi-fi Direction C - Ecrans 1 et 3.html.
 */

declare(strict_types=1);

require __DIR__ . '/db.php';

$pdo = get_pdo();

// Top 3 offres pour le moment (Phase 1 : on en a 1, infra prête pour 3)
$top = $pdo->query("
    SELECT
        o.id, o.type, o.name,
        o.monthly_price, o.promo_price, o.promo_duration_months,
        o.commitment_months, o.score,
        op.name AS operator_name, op.slug AS operator_slug,
        fs.download_mbps, fs.upload_mbps, fs.technology, fs.wifi_standard
    FROM offers o
    JOIN operators op ON op.id = o.operator_id
    LEFT JOIN fibre_specs fs ON fs.offer_id = o.id
    WHERE o.is_active = TRUE
    ORDER BY (o.score IS NULL), o.score DESC, o.monthly_price ASC
    LIMIT 3
")->fetchAll();

$operators = $pdo->query('SELECT slug, name FROM operators ORDER BY name')->fetchAll();

$lastUpdate = $pdo->query('SELECT MAX(last_scraped_at) FROM offers')->fetchColumn();

// Helpers
function fmt_price(float $price): string {
    return number_format($price, 2, ',', ' ') . ' €';
}
function e(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}
function type_label(string $type): string {
    return match ($type) {
        'fibre'  => 'Fibre',
        'mobile' => 'Mobile',
        'bundle' => 'Bundle',
        default  => $type,
    };
}

$pageTitle = 'Comparateur télécom FR — Accueil';
require __DIR__ . '/partials/header.php';
?>
<main class="page">

    <section class="home-hero">
        <span class="acid-kicker">Mis à jour quotidiennement</span>
        <h1 class="home-hero__title">
            Comparez les offres télécom des 4 opérateurs français
        </h1>
        <p class="t-body home-hero__sub">
            Orange, SFR, Bouygues et Free, agrégés en un coup d'œil. Données informatives,
            non contractuelles, mises à jour automatiquement chaque jour.
        </p>
    </section>

    <form class="home-search" method="get" action="results.php">
        <div class="home-search__row">
            <div class="filter-field">
                <label for="h-operator">Opérateur</label>
                <select id="h-operator" name="operator">
                    <option value="all">Tous</option>
                    <?php foreach ($operators as $op): ?>
                        <option value="<?= e($op['slug']) ?>"><?= e($op['name']) ?></option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="filter-field">
                <label>Type d'offre</label>
                <div class="segmented" role="radiogroup" aria-label="Type d'offre">
                    <input type="radio" id="h-t-all"    name="type" value="all" checked>
                    <label for="h-t-all">Tous</label>
                    <input type="radio" id="h-t-fibre"  name="type" value="fibre">
                    <label for="h-t-fibre">Fibre</label>
                    <input type="radio" id="h-t-mobile" name="type" value="mobile">
                    <label for="h-t-mobile">Mobile</label>
                    <input type="radio" id="h-t-bundle" name="type" value="bundle">
                    <label for="h-t-bundle">Bundle</label>
                </div>
            </div>

            <div class="filter-field">
                <label for="h-max">Prix max (€/mois)</label>
                <input id="h-max" type="number" name="max_price" min="0" step="1" placeholder="60">
            </div>
        </div>

        <div class="home-search__cta">
            <button type="submit" class="btn-primary">Rechercher</button>
        </div>
    </form>

    <section class="section">
        <div class="section__head">
            <h2 class="t-h1 section__title">Top offres du moment</h2>
            <p class="section__sub">
                <?= count($top) ?> offre<?= count($top) > 1 ? 's' : '' ?> sélectionnée<?= count($top) > 1 ? 's' : '' ?>
                — triées par score décroissant, prix croissant.
            </p>
        </div>

        <?php if (empty($top)): ?>
            <div class="empty-state">
                <p class="t-h2">Aucune offre indexée pour l'instant</p>
                <p class="t-body">Le pipeline de scraping est en cours de constitution.</p>
            </div>
        <?php else: ?>
            <div class="results-grid">
                <?php foreach ($top as $offer): require __DIR__ . '/partials/offer-card.php'; endforeach; ?>
            </div>
        <?php endif; ?>
    </section>

<?php require __DIR__ . '/partials/footer.php'; ?>
