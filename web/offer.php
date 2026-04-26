<?php
/**
 * Écran 3 — offer.php
 * Détail d'une offre. 3 cas : id manquant/non numérique → 400, id inconnu → 404, OK.
 * Cf. 00_brief/screens.md écran 3 (Phase 1) et 00_brief/dc/Hi-fi Direction C - Ecrans 1 et 3.html.
 */

declare(strict_types=1);

require __DIR__ . '/db.php';

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

function render_error(int $code, string $title, string $message): void {
    http_response_code($code);
    $pageTitle = "Comparateur télécom FR — Erreur $code";
    require __DIR__ . '/partials/header.php';
    ?>
    <main class="page">
        <div class="error-page">
            <div class="error-page__code"><?= e((string)$code) ?></div>
            <h1 class="t-h1 error-page__title"><?= e($title) ?></h1>
            <p class="error-page__msg"><?= e($message) ?></p>
            <a class="btn-primary" href="results.php">Voir le catalogue</a>
        </div>
    <?php require __DIR__ . '/partials/footer.php';
    exit;
}

// ─── 400 : id absent ou non numérique ───────────────────────────────
$idRaw = $_GET['id'] ?? null;
if ($idRaw === null || !ctype_digit((string)$idRaw)) {
    render_error(
        400,
        'Paramètre manquant',
        "L'identifiant de l'offre est requis et doit être un entier positif. Exemple : offer.php?id=1"
    );
}

$offerId = (int) $idRaw;
$pdo = get_pdo();

$stmt = $pdo->prepare("
    SELECT
        o.id, o.type, o.name,
        o.monthly_price, o.promo_price, o.promo_duration_months,
        o.commitment_months, o.setup_fee, o.source_url, o.score,
        o.last_scraped_at,
        op.name AS operator_name, op.slug AS operator_slug,
        op.website_url AS operator_website,
        fs.download_mbps, fs.upload_mbps, fs.technology, fs.wifi_standard,
        fs.has_tv, fs.tv_channels_count, fs.has_landline
    FROM offers o
    JOIN operators op ON op.id = o.operator_id
    LEFT JOIN fibre_specs fs ON fs.offer_id = o.id
    WHERE o.id = :id AND o.is_active = TRUE
");
$stmt->execute(['id' => $offerId]);
$offer = $stmt->fetch();

// ─── 404 : id inconnu ───────────────────────────────────────────────
if (!$offer) {
    render_error(
        404,
        "Cette offre n'existe pas ou plus",
        "L'offre demandée a peut-être été retirée du catalogue ou son identifiant est invalide."
    );
}

// ─── Options associées ──────────────────────────────────────────────
$optStmt = $pdo->prepare("
    SELECT opt.name, opt.category, oo.is_included, oo.extra_price
    FROM offer_options oo
    JOIN options opt ON opt.id = oo.option_id
    WHERE oo.offer_id = :id
    ORDER BY opt.id
");
$optStmt->execute(['id' => $offerId]);
$options = $optStmt->fetchAll();

// ─── Historique des prix (Phase 2A.8) ───────────────────────────────
$historyStmt = $pdo->prepare("
    SELECT monthly_price, captured_at, is_simulated
    FROM prices_history
    WHERE offer_id = :id
    ORDER BY captured_at ASC
");
$historyStmt->execute(['id' => $offerId]);
$priceHistoryRows = $historyStmt->fetchAll();

$priceHistory = array_map(fn($r) => [
    'price'        => (float) $r['monthly_price'],
    'captured_at'  => $r['captured_at'],
    'is_simulated' => (bool) $r['is_simulated'],
], $priceHistoryRows);
$historyHasSimulated = (bool) array_filter($priceHistory, fn($p) => $p['is_simulated']);

// Préparation affichage
$hasPromo  = $offer['promo_price'] !== null;
$savings   = $hasPromo ? max(0, (float)$offer['monthly_price'] - (float)$offer['promo_price']) : 0;
$shownMain = $hasPromo ? (float)$offer['promo_price'] : (float)$offer['monthly_price'];
$score     = $offer['score'];
$scorePct  = $score !== null ? round(((float)$score / 10) * 100) : 0;

$pageTitle = 'Comparateur télécom FR — ' . $offer['name'];
require __DIR__ . '/partials/header.php';
?>
<main class="detail-page">

    <div class="detail-bar">
        <a class="btn-ghost" href="results.php">← Retour au catalogue</a>
        <span class="detail-bar__ref">offer/<?= (int)$offer['id'] ?></span>
    </div>

    <header class="detail-hero">
        <div class="op-logo" aria-hidden="true">
            <?= e(strtoupper(substr((string)$offer['operator_name'], 0, 1))) ?>
        </div>
        <div class="detail-hero__body">
            <span class="t-caption detail-hero__operator">
                <?= e(strtoupper((string)$offer['operator_name'])) ?>
            </span>
            <h1 class="t-h1 detail-hero__name"><?= e($offer['name']) ?></h1>
            <ul class="detail-hero__badges">
                <li class="badge badge--type"><?= e(type_label($offer['type'])) ?></li>
                <?php if (!empty($offer['technology'])): ?>
                    <li class="badge"><?= e($offer['technology']) ?></li>
                <?php endif; ?>
                <?php if (!empty($offer['wifi_standard'])): ?>
                    <li class="badge"><?= e($offer['wifi_standard']) ?></li>
                <?php endif; ?>
                <li class="badge">
                    <?= ((int)$offer['commitment_months']) === 0 ? 'Sans engagement' : ((int)$offer['commitment_months']) . ' mois' ?>
                </li>
            </ul>
        </div>
    </header>

    <section class="detail-price">
        <div class="detail-price__line">
            <span class="detail-price__main"><?= fmt_price($shownMain) ?></span>
            <span class="t-caption">/mois</span>
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
                puis <?= fmt_price((float)$offer['monthly_price']) ?>/mois.
                Frais de mise en service : <?= fmt_price((float)$offer['setup_fee']) ?>.
            </span>
        <?php else: ?>
            <span class="t-caption price-fineprint">
                Frais de mise en service : <?= fmt_price((float)$offer['setup_fee']) ?>.
            </span>
        <?php endif; ?>
    </section>

    <section class="detail-block">
        <div class="detail-block__head">
            <h2 class="t-h2 detail-block__title">Évolution du prix</h2>
        </div>
        <?php if (count($priceHistory) < 5): ?>
            <div class="options-empty">
                Historique en cours de constitution. Revenez dans quelques jours.
            </div>
        <?php else: ?>
            <div class="price-chart">
                <canvas id="price-chart" height="200" aria-label="Graphique d'évolution du prix mensuel"></canvas>
            </div>
            <?php if ($historyHasSimulated): ?>
                <p class="price-chart__disclaimer">
                    Historique reconstitué à partir de données de démonstration.
                    La collecte automatisée alimentera ce graphique avec des
                    données réelles à partir du <?= e(date('d/m/Y', strtotime('+1 day'))) ?>.
                </p>
            <?php endif; ?>
            <script>
              window.__priceHistory = <?= json_encode($priceHistory, JSON_UNESCAPED_UNICODE) ?>;
            </script>
        <?php endif; ?>
    </section>

    <?php if (!empty($offer['technology'])): // bloc fibre Phase 1 ?>
    <section class="detail-block">
        <div class="detail-block__head">
            <h2 class="t-h2 detail-block__title">Spécifications techniques</h2>
        </div>
        <div class="specs">
            <?php if (!empty($offer['download_mbps'])): ?>
                <div class="specs__row">
                    <span class="specs__label">Débit descendant</span>
                    <span class="specs__value"><?= e(number_format((int)$offer['download_mbps'])) ?> Mbps</span>
                </div>
            <?php endif; ?>
            <?php if (!empty($offer['upload_mbps'])): ?>
                <div class="specs__row">
                    <span class="specs__label">Débit montant</span>
                    <span class="specs__value"><?= e(number_format((int)$offer['upload_mbps'])) ?> Mbps</span>
                </div>
            <?php endif; ?>
            <div class="specs__row">
                <span class="specs__label">Technologie</span>
                <span class="specs__value"><?= e((string)$offer['technology']) ?></span>
            </div>
            <?php if (!empty($offer['wifi_standard'])): ?>
                <div class="specs__row">
                    <span class="specs__label">WiFi</span>
                    <span class="specs__value"><?= e((string)$offer['wifi_standard']) ?></span>
                </div>
            <?php endif; ?>
            <div class="specs__row">
                <span class="specs__label">TV</span>
                <span class="specs__value">
                    <?php if ((int)$offer['has_tv']): ?>
                        Incluse<?= $offer['tv_channels_count'] ? ' · ' . (int)$offer['tv_channels_count'] . ' chaînes' : '' ?>
                    <?php else: ?>
                        Non incluse
                    <?php endif; ?>
                </span>
            </div>
            <div class="specs__row">
                <span class="specs__label">Téléphonie fixe</span>
                <span class="specs__value">
                    <?= ((int)$offer['has_landline']) ? 'Incluse' : 'Non incluse' ?>
                </span>
            </div>
        </div>
    </section>
    <?php endif; ?>

    <section class="detail-block">
        <div class="detail-block__head">
            <h2 class="t-h2 detail-block__title">Options</h2>
        </div>
        <?php if (empty($options)): ?>
            <div class="options-empty">
                Aucune option indexée pour l'instant — les options seront ingérées
                en Phase 1.5 / Phase 2 via le scraper.
            </div>
        <?php else: ?>
            <ul class="results-grid" style="grid-template-columns: 1fr 1fr;">
                <?php foreach ($options as $opt): ?>
                    <li class="badge"><?= e($opt['name']) ?></li>
                <?php endforeach; ?>
            </ul>
        <?php endif; ?>
    </section>

    <section class="detail-block offer-card__score">
        <div class="detail-block__head">
            <h2 class="t-h2 detail-block__title">Score qualité/prix</h2>
            <a href="about.php#score" class="page-footer__link" style="font-size:.8125rem;">Comment est calculé ce score ?</a>
        </div>
        <div class="offer-card__score-row">
            <span class="t-caption">Score</span>
            <span class="score-value">
                <?= $score !== null ? e(number_format((float)$score, 1, ',', '')) . ' / 10' : '—' ?>
            </span>
        </div>
        <div class="score-bar detail-score-bar <?= $score === null ? 'is-empty' : '' ?>">
            <div class="fill" data-score="<?= e((string)$scorePct) ?>"
                 <?= $score !== null ? 'style="width:' . (int)$scorePct . '%"' : '' ?>></div>
        </div>
    </section>

    <div class="detail-cta">
        <a class="btn-primary" href="<?= e((string)$offer['source_url']) ?>"
           target="_blank" rel="noopener noreferrer">
            Voir l'offre originale ↗
        </a>
    </div>

    <section class="phase2-placeholder">
        <strong>Phase 2 — à venir sur cette page :</strong>
        <ul>
            <li>Historique des prix sur les 30 derniers jours</li>
            <li>Couverture ARCEP par commune (mobile + fibre)</li>
            <li>Comparaison radar 6 axes vs moyenne marché</li>
        </ul>
    </section>

    <p class="detail-meta">
        Dernière mise à jour : <?= e((string)$offer['last_scraped_at']) ?>
    </p>

<?php if (count($priceHistory) >= 5): ?>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js" defer></script>
<script src="assets/js/price-chart.js" defer></script>
<?php endif; ?>
<?php require __DIR__ . '/partials/footer.php'; ?>
