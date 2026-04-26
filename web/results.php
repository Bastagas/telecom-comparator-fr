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

$pageTitle = 'Comparateur télécom FR — Résultats';
require __DIR__ . '/partials/header.php';
?>
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
            <?php foreach ($offers as $offer): require __DIR__ . '/partials/offer-card.php'; endforeach; ?>
        </section>
    <?php endif; ?>

<?php require __DIR__ . '/partials/footer.php'; ?>
