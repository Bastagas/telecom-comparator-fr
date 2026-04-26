<?php
/**
 * Écran 2 — results.php
 * Liste des offres filtrées (Phase 1 = fibre uniquement, 1 offre Free).
 * Cf. 00_brief/screens.md écran 2 et 00_brief/dc/* pour le design.
 */

declare(strict_types=1);

require __DIR__ . '/db.php';

// ─── Filtres GET ─────────────────────────────────────────────────────
$filters = [
    'operator'  => $_GET['operator']  ?? '',
    'type'      => $_GET['type']      ?? '',
    'max_price' => $_GET['max_price'] ?? '',
];

// ─── Query SQL ───────────────────────────────────────────────────────
$sql = "
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
";
$params = [];

if ($filters['operator'] !== '' && $filters['operator'] !== 'all') {
    $sql .= ' AND op.slug = :operator';
    $params['operator'] = $filters['operator'];
}
if ($filters['type'] !== '' && $filters['type'] !== 'all') {
    $sql .= ' AND o.type = :type';
    $params['type'] = $filters['type'];
}
if ($filters['max_price'] !== '' && is_numeric($filters['max_price'])) {
    $sql .= ' AND o.monthly_price <= :max_price';
    $params['max_price'] = (float) $filters['max_price'];
}

$sql .= ' ORDER BY (o.score IS NULL), o.score DESC, o.monthly_price ASC';

$pdo = get_pdo();
$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$offers = $stmt->fetchAll();

// Liste des opérateurs pour le filtre
$operators = $pdo->query('SELECT slug, name FROM operators ORDER BY name')->fetchAll();

// ─── Helpers d'affichage ────────────────────────────────────────────
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
?><!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Comparateur télécom FR — Résultats</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="assets/css/tokens.css">
<link rel="stylesheet" href="assets/css/components.css">
<link rel="stylesheet" href="assets/css/layout.css">
</head>
<body>
<main class="page">

    <header class="page-header">
        <span class="t-caption page-header__kicker">Phase 1 · Walking skeleton</span>
        <h1 class="t-display page-header__title">Résultats</h1>
        <p class="t-body page-header__sub">
            Offres télécom des opérateurs français, mises à jour quotidiennement.
            Données informatives, non contractuelles.
        </p>
    </header>

    <form class="filters" method="get" action="results.php">
        <div class="filter-field">
            <label for="f-operator">Opérateur</label>
            <select id="f-operator" name="operator">
                <option value="all">Tous</option>
                <?php foreach ($operators as $op): ?>
                    <option value="<?= e($op['slug']) ?>"
                        <?= $filters['operator'] === $op['slug'] ? 'selected' : '' ?>>
                        <?= e($op['name']) ?>
                    </option>
                <?php endforeach; ?>
            </select>
        </div>

        <div class="filter-field">
            <label for="f-type">Type</label>
            <select id="f-type" name="type">
                <option value="all">Tous</option>
                <option value="fibre"  <?= $filters['type']==='fibre'?'selected':'' ?>>Fibre</option>
                <option value="mobile" <?= $filters['type']==='mobile'?'selected':'' ?>>Mobile</option>
                <option value="bundle" <?= $filters['type']==='bundle'?'selected':'' ?>>Bundle</option>
            </select>
        </div>

        <div class="filter-field">
            <label for="f-max">Prix max (€/mois)</label>
            <input id="f-max" type="number" name="max_price" min="0" step="1"
                   value="<?= e((string)$filters['max_price']) ?>" placeholder="60">
        </div>

        <div class="filters__actions">
            <button type="submit" class="btn-primary">Filtrer</button>
        </div>
    </form>

    <div class="results-meta">
        <span class="t-caption"><?= count($offers) ?> résultat<?= count($offers)>1?'s':'' ?></span>
    </div>

    <?php if (empty($offers)): ?>
        <div class="empty-state">
            <p class="t-h2">Aucune offre ne correspond à vos critères</p>
            <p class="t-body">Essayez d'élargir le prix ou de retirer un filtre.</p>
        </div>
    <?php else: ?>
        <section class="results-grid">
            <?php foreach ($offers as $offer):
                $hasPromo  = $offer['promo_price'] !== null;
                $savings   = $hasPromo ? max(0, (float)$offer['monthly_price'] - (float)$offer['promo_price']) : 0;
                $shownMain = $hasPromo ? (float)$offer['promo_price'] : (float)$offer['monthly_price'];
                $score     = $offer['score'];
                $scorePct  = $score !== null ? round(((float)$score / 10) * 100) : 0;
            ?>
            <article class="offer-card" tabindex="0" data-score="<?= e((string)$scorePct) ?>">
                <header class="offer-card__head">
                    <span class="t-caption"><?= e(strtoupper((string)$offer['operator_name'])) ?></span>
                    <span class="badge badge--type"><?= e(type_label($offer['type'])) ?></span>
                </header>

                <h2 class="t-h1 offer-card__name"><?= e($offer['name']) ?></h2>

                <ul class="offer-card__badges">
                    <?php if ($offer['technology']): ?>
                        <li class="badge"><?= e($offer['technology']) ?></li>
                    <?php endif; ?>
                    <?php if ($offer['wifi_standard']): ?>
                        <li class="badge"><?= e($offer['wifi_standard']) ?></li>
                    <?php endif; ?>
                    <li class="badge">
                        <?= ((int)$offer['commitment_months']) === 0 ? 'Sans engagement' : ((int)$offer['commitment_months']) . ' mois' ?>
                    </li>
                    <?php if ($offer['download_mbps']): ?>
                        <li class="badge"><?= e((string)number_format((int)$offer['download_mbps'])) ?> Mbps↓</li>
                    <?php endif; ?>
                </ul>

                <div class="offer-card__price">
                    <div class="price-line">
                        <span class="t-display price-main"><?= fmt_price($shownMain) ?></span>
                        <span class="t-caption price-unit">/mois</span>
                    </div>
                    <?php if ($hasPromo): ?>
                        <div class="offer-card__price-context">
                            <span class="price-strikethrough"><?= fmt_price((float)$offer['monthly_price']) ?></span>
                            <?php if ($savings > 0): ?>
                                <span class="acid-pill">Économisez <?= fmt_price($savings) ?></span>
                            <?php endif; ?>
                        </div>
                        <span class="t-caption price-fineprint">
                            Tarif promo
                            <?= $offer['promo_duration_months'] ? ((int)$offer['promo_duration_months']) . ' mois' : '' ?>,
                            puis <?= fmt_price((float)$offer['monthly_price']) ?>/mois
                        </span>
                    <?php endif; ?>
                </div>

                <div class="offer-card__score">
                    <div class="offer-card__score-row">
                        <span class="t-caption">Score</span>
                        <span class="score-value">
                            <?= $score !== null ? e(number_format((float)$score, 1, ',', '')) . ' / 10' : '—' ?>
                        </span>
                    </div>
                    <div class="score-bar <?= $score === null ? 'is-empty' : '' ?>">
                        <div class="fill" data-score="<?= e((string)$scorePct) ?>"></div>
                    </div>
                </div>

                <a class="btn-primary" href="offer.php?id=<?= (int)$offer['id'] ?>">
                    Voir le détail →
                </a>
            </article>
            <?php endforeach; ?>
        </section>
    <?php endif; ?>

    <footer class="page-footer">
        <span>Sources : sites des opérateurs · ARCEP (Phase 2)</span>
        <span>Données informatives, non contractuelles. Vérifier sur le site officiel avant souscription.</span>
    </footer>

</main>
<script src="assets/js/animations.js" defer></script>
</body>
</html>
