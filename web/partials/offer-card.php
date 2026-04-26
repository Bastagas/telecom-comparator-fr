<?php
/**
 * Composant carte d'offre — réutilisé sur results.php et index.php.
 *
 * Variables d'entrée :
 *   $offer (array) : ligne SQL avec au minimum
 *     id, type, name, monthly_price, promo_price, promo_duration_months,
 *     commitment_months, score, operator_name
 *   et éventuellement (LEFT JOIN fibre_specs) :
 *     download_mbps, upload_mbps, technology, wifi_standard
 *
 * Helpers attendus en scope (cf. results.php / index.php) :
 *   fmt_price(float), e(string), type_label(string)
 */
declare(strict_types=1);

$hasPromo  = $offer['promo_price'] !== null;
$savings   = $hasPromo ? max(0, (float)$offer['monthly_price'] - (float)$offer['promo_price']) : 0;
$shownMain = $hasPromo ? (float)$offer['promo_price'] : (float)$offer['monthly_price'];
$score     = $offer['score'];
$scorePct  = $score !== null ? round(((float)$score / 10) * 100) : 0;
?>
<article class="offer-card" tabindex="0">
    <header class="offer-card__head">
        <span class="t-caption"><?= e(strtoupper((string)$offer['operator_name'])) ?></span>
        <span class="badge badge--type"><?= e(type_label($offer['type'])) ?></span>
    </header>

    <h2 class="t-h1 offer-card__name"><?= e($offer['name']) ?></h2>

    <ul class="offer-card__badges">
        <?php if (!empty($offer['technology'])): ?>
            <li class="badge"><?= e($offer['technology']) ?></li>
        <?php endif; ?>
        <?php if (!empty($offer['wifi_standard'])): ?>
            <li class="badge"><?= e($offer['wifi_standard']) ?></li>
        <?php endif; ?>
        <li class="badge">
            <?= ((int)$offer['commitment_months']) === 0 ? 'Sans engagement' : ((int)$offer['commitment_months']) . ' mois' ?>
        </li>
        <?php if (!empty($offer['download_mbps'])): ?>
            <li class="badge"><?= e(number_format((int)$offer['download_mbps'])) ?> Mbps↓</li>
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
