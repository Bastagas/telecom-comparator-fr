<?php
/**
 * Écran 2 — results.php
 * Liste des offres filtrées (Phase 1 = fibre uniquement, 1 offre Free).
 * Cf. 00_brief/screens.md écran 2 et 00_brief/dc/* pour le design.
 */

declare(strict_types=1);

require __DIR__ . '/db.php';

const PER_PAGE = 6;

// ─── Filtres GET ─────────────────────────────────────────────────────
$filters = [
    'operator'     => $_GET['operator']     ?? '',
    'type'         => $_GET['type']         ?? '',
    'max_price'    => $_GET['max_price']    ?? '',
    'min_download' => $_GET['min_download'] ?? '',
    'has_promo'    => isset($_GET['has_promo']) && $_GET['has_promo'] === '1',
    'sort'         => $_GET['sort']         ?? 'score',
];

// ─── Construction du WHERE (bindings PDO) ────────────────────────────
$where = ['o.is_active = TRUE'];
$params = [];

if ($filters['operator'] !== '' && $filters['operator'] !== 'all') {
    $where[] = 'op.slug = :operator';
    $params['operator'] = $filters['operator'];
}
if ($filters['type'] !== '' && $filters['type'] !== 'all') {
    $where[] = 'o.type = :type';
    $params['type'] = $filters['type'];
}
if ($filters['max_price'] !== '' && is_numeric($filters['max_price'])) {
    $where[] = 'o.monthly_price <= :max_price';
    $params['max_price'] = (float) $filters['max_price'];
}
if ($filters['min_download'] !== '' && is_numeric($filters['min_download'])) {
    $where[] = 'fs.download_mbps >= :min_download';
    $params['min_download'] = (int) $filters['min_download'];
}
if ($filters['has_promo']) {
    $where[] = 'o.promo_price IS NOT NULL';
}

$where_sql = implode(' AND ', $where);

// ─── Tri (whitelist pour empêcher l'injection) ──────────────────────
$sort_options = [
    'score'      => 'ORDER BY (o.score IS NULL), o.score DESC, o.monthly_price ASC',
    'price_asc'  => 'ORDER BY o.monthly_price ASC',
    'price_desc' => 'ORDER BY o.monthly_price DESC',
];
$sort_key = isset($sort_options[$filters['sort']]) ? $filters['sort'] : 'score';
$order_by = $sort_options[$sort_key];

// ─── Pagination — COUNT total avant LIMIT/OFFSET ─────────────────────
$page = max(1, (int) ($_GET['page'] ?? 1));

$pdo = get_pdo();
$count_sql = "
    SELECT COUNT(*)
    FROM offers o
    JOIN operators op ON op.id = o.operator_id
    LEFT JOIN fibre_specs fs ON fs.offer_id = o.id
    WHERE $where_sql
";
$count_stmt = $pdo->prepare($count_sql);
$count_stmt->execute($params);
$total = (int) $count_stmt->fetchColumn();

$total_pages = max(1, (int) ceil($total / PER_PAGE));
$page = min($page, $total_pages);
$offset = ($page - 1) * PER_PAGE;

// ─── Query SQL paginée ───────────────────────────────────────────────
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
    WHERE $where_sql
    $order_by
    LIMIT :limit OFFSET :offset
";

$stmt = $pdo->prepare($sql);
foreach ($params as $k => $v) {
    $stmt->bindValue(":$k", $v);
}
$stmt->bindValue(':limit', PER_PAGE, PDO::PARAM_INT);
$stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
$stmt->execute();
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
function build_query_string(array $base, array $override = []): string {
    $merged = array_merge($base, $override);
    $clean = [];
    foreach ($merged as $k => $v) {
        if ($v === '' || $v === null || $v === false) continue;
        $clean[$k] = $v === true ? '1' : $v;
    }
    return http_build_query($clean);
}

// Paramètres GET à propager dans la pagination
$query_params = [
    'operator'     => $filters['operator'] !== 'all' ? $filters['operator'] : '',
    'type'         => $filters['type'] !== 'all'     ? $filters['type']     : '',
    'max_price'    => $filters['max_price'],
    'min_download' => $filters['min_download'],
    'has_promo'    => $filters['has_promo'] ? '1' : '',
    'sort'         => $sort_key !== 'score' ? $sort_key : '',
];

// Compte les filtres actifs (pour décider d'afficher le bouton "Réinitialiser")
$active_filters_count = 0;
foreach (['operator', 'type'] as $k) {
    if ($filters[$k] !== '' && $filters[$k] !== 'all') $active_filters_count++;
}
foreach (['max_price', 'min_download'] as $k) {
    if ($filters[$k] !== '') $active_filters_count++;
}
if ($filters['has_promo']) $active_filters_count++;
if ($sort_key !== 'score') $active_filters_count++;

$sort_labels = [
    'score'      => 'Score',
    'price_asc'  => 'Prix croissant',
    'price_desc' => 'Prix décroissant',
];

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

        <div class="filter-field">
            <label for="f-min-down">Débit min ↓ (Mbps)</label>
            <input id="f-min-down" type="number" name="min_download" min="0" step="500"
                   value="<?= e((string)$filters['min_download']) ?>" placeholder="1000">
        </div>

        <div class="filter-field">
            <label for="f-sort">Trier par</label>
            <select id="f-sort" name="sort">
                <option value="score"      <?= $sort_key==='score'?'selected':'' ?>>Score (recommandé)</option>
                <option value="price_asc"  <?= $sort_key==='price_asc'?'selected':'' ?>>Prix croissant</option>
                <option value="price_desc" <?= $sort_key==='price_desc'?'selected':'' ?>>Prix décroissant</option>
            </select>
        </div>

        <div class="filter-field filter-field--checkbox">
            <label class="checkbox-label">
                <input type="checkbox" name="has_promo" value="1"
                       <?= $filters['has_promo'] ? 'checked' : '' ?>>
                <span>Avec promo</span>
            </label>
        </div>

        <div class="filters__actions">
            <button type="submit" class="btn-primary">Filtrer</button>
        </div>
    </form>

    <div class="results-header">
        <div class="results-header__count">
            <strong><?= $total ?></strong>
            <span>résultat<?= $total > 1 ? 's' : '' ?></span>
            <?php if ($active_filters_count > 0): ?>
                <a href="results.php" class="results-header__reset">Réinitialiser les filtres</a>
            <?php endif; ?>
        </div>
        <span class="results-header__sort-active">
            Trié par <strong><?= e($sort_labels[$sort_key]) ?></strong>
        </span>
    </div>

    <?php if ($total === 0): ?>
        <div class="empty-state">
            <p class="t-h2">Aucune offre ne correspond à vos critères</p>
            <p class="t-body">Essayez d'élargir le prix ou de retirer un filtre.</p>
        </div>
    <?php else: ?>
        <section class="results-grid">
            <?php foreach ($offers as $offer): require __DIR__ . '/partials/offer-card.php'; endforeach; ?>
        </section>

        <?php if ($total_pages > 1): ?>
            <nav class="pagination" aria-label="Pagination des résultats">
                <?php if ($page > 1): ?>
                    <a class="pagination__btn"
                       href="?<?= e(build_query_string($query_params, ['page' => $page - 1])) ?>">← Précédent</a>
                <?php else: ?>
                    <span class="pagination__btn pagination__btn--disabled" aria-disabled="true">← Précédent</span>
                <?php endif; ?>

                <span class="pagination__pages">Page <?= $page ?> / <?= $total_pages ?></span>

                <?php if ($page < $total_pages): ?>
                    <a class="pagination__btn"
                       href="?<?= e(build_query_string($query_params, ['page' => $page + 1])) ?>">Suivant →</a>
                <?php else: ?>
                    <span class="pagination__btn pagination__btn--disabled" aria-disabled="true">Suivant →</span>
                <?php endif; ?>
            </nav>
        <?php endif; ?>
    <?php endif; ?>

<?php require __DIR__ . '/partials/footer.php'; ?>
