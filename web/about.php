<?php
/**
 * Page Méthodologie & sources — about.php
 * Documente la formule du score, les sources, les limites assumées.
 * Cf. JOURNAL Tâche 2A.9.
 */

declare(strict_types=1);

require __DIR__ . '/db.php';

function e(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}

$pdo = get_pdo();
$lastUpdate = $pdo->query('SELECT MAX(last_scraped_at) FROM offers')->fetchColumn();

$pageTitle = 'Comparateur télécom FR — Méthodologie';
require __DIR__ . '/partials/header.php';
?>
<main class="about-page">

    <header class="about-hero">
        <h1 class="about-hero__title">Méthodologie et sources</h1>
        <p class="about-hero__sub">
            Cette page documente comment nos chiffres sont calculés, d'où ils viennent,
            et ce que ce comparateur ne capture pas. La transparence prime sur la promesse.
        </p>
    </header>

    <section class="about-section" id="scope">
        <h2 class="t-h1 about-section__title">Que fait ce comparateur ?</h2>
        <p>
            Le projet agrège les <strong>offres commerciales fibre des 4 opérateurs
            télécom français</strong> (Orange, SFR, Bouygues, Free) en une vue unifiée
            comparable. Phase 2A : 9 offres fibre. Le mobile arrivera en Phase 2B,
            couplé aux données régulateur ARCEP de couverture.
        </p>
        <p>
            Les prix et caractéristiques sont collectés <strong>quotidiennement</strong>
            par un pipeline de scraping Python qui interroge les pages tarifaires
            officielles des opérateurs. Les données ARCEP (couverture par commune)
            seront intégrées en Phase 2B avec une mise à jour trimestrielle —
            c'est la cadence officielle de publication ARCEP.
        </p>
        <p>
            Les informations affichées sont <strong>informatives, non contractuelles</strong>.
            Vérifiez systématiquement sur le site de l'opérateur avant de souscrire :
            les tarifs et conditions peuvent varier selon votre éligibilité, votre code
            postal, et les promotions en cours.
        </p>
    </section>

    <section class="about-section" id="score">
        <h2 class="t-h1 about-section__title">Le score composite — comment il est calculé</h2>
        <p>
            Chaque offre se voit attribuer un <strong>score sur 10</strong>, calculé
            en agrégeant 6 variables comparées au panel actuel du marché. Plus le
            score est élevé, plus l'offre est compétitive sur la combinaison
            prix / débit / engagement / valeur ajoutée.
        </p>

        <div class="about-table">
            <div class="about-table__row about-table__row--head">
                <span>Variable</span>
                <span>Poids</span>
                <span>Justification</span>
            </div>
            <div class="about-table__row">
                <span>Prix mensuel</span>
                <span class="about-table__weight">35 %</span>
                <span class="about-table__why">Critère #1 pour une majorité de consommateurs.</span>
            </div>
            <div class="about-table__row">
                <span>Débit descendant</span>
                <span class="about-table__weight">25 %</span>
                <span class="about-table__why">Différentiateur technique principal de la fibre.</span>
            </div>
            <div class="about-table__row">
                <span>Options incluses</span>
                <span class="about-table__weight">15 %</span>
                <span class="about-table__why">Valeur ajoutée non-prix : streaming, TV, cloud.</span>
            </div>
            <div class="about-table__row">
                <span>Engagement</span>
                <span class="about-table__weight">10 %</span>
                <span class="about-table__why">Liberté commerciale (sans engagement = score plein).</span>
            </div>
            <div class="about-table__row">
                <span>Frais d'installation</span>
                <span class="about-table__weight">10 %</span>
                <span class="about-table__why">Coût d'entrée à amortir sur la durée d'abonnement.</span>
            </div>
            <div class="about-table__row">
                <span>Bonus techno</span>
                <span class="about-table__weight">5 %</span>
                <span class="about-table__why">Wi-Fi 7 et débit montant ≥ 700 Mbps : valorisation premium.</span>
            </div>
        </div>

        <div class="about-note">
            <strong>Note méthodologique.</strong> La formule est volontairement
            transparente — elle reflète des choix d'auteur et peut être discutée.
            Le poids du prix (35 %) est justifié par les enquêtes consommateurs ;
            l'arbitrage débit/options/engagement est un compromis. Une 7<sup>e</sup>
            variable « qualité réseau » sera ajoutée en Phase 2B avec les données
            ARCEP, ce qui entraînera un recalibrage des pondérations actuelles.
        </div>

        <p>
            Pour les variables continues (prix, débit, frais), le calcul utilise
            une normalisation min-max sur le panel actif. Si une variable n'a
            qu'une seule valeur dans tout le marché (cas extrême : 1 seul opérateur
            référencé), le score est neutre (7,5/10) sur cette dimension — pour
            éviter que l'arrivée d'une seconde offre ne fasse sauter brutalement
            tous les scores.
        </p>
    </section>

    <section class="about-section" id="sources">
        <h2 class="t-h1 about-section__title">Sources</h2>
        <p>Phase 2A — sites tarifaires officiels des 4 opérateurs :</p>
        <ul>
            <li>
                <a href="https://www.orange.fr" target="_blank" rel="noopener noreferrer">Orange&nbsp;↗</a>
                — gamme Livebox (Classic, Up, Max).
            </li>
            <li>
                <a href="https://www.sfr.fr" target="_blank" rel="noopener noreferrer">SFR&nbsp;↗</a>
                — SFR Fibre Power et Premium.
            </li>
            <li>
                <a href="https://www.bouyguestelecom.fr" target="_blank" rel="noopener noreferrer">Bouygues Telecom&nbsp;↗</a>
                — Bbox Fit, Must, Ultym.
            </li>
            <li>
                <a href="https://www.free.fr" target="_blank" rel="noopener noreferrer">Free&nbsp;↗</a>
                — Freebox Pop.
            </li>
        </ul>
        <p>Phase 2B (à venir) — données régulateur ARCEP :</p>
        <ul>
            <li>
                <a href="https://data.arcep.fr/" target="_blank" rel="noopener noreferrer">data.arcep.fr&nbsp;↗</a>
                — Mon Réseau Mobile (couverture 4G/5G par commune × opérateur)
                et Observatoire du Très Haut Débit (couverture fibre par commune).
                Mise à jour trimestrielle.
            </li>
        </ul>
    </section>

    <section class="about-section" id="limits">
        <h2 class="t-h1 about-section__title">Limites assumées</h2>
        <ul>
            <li>
                <strong>Données informatives.</strong> Les prix et conditions affichés
                proviennent de pages publiques scrapées la nuit précédente. Ils peuvent
                avoir changé entre-temps. Toujours vérifier sur le site de l'opérateur
                avant souscription.
            </li>
            <li>
                <strong>Pas d'éligibilité par adresse.</strong> Le service ne teste pas
                votre éligibilité à la fibre par adresse exacte. Cette fonctionnalité
                est prévue en Phase 3 via l'API Adresse BAN du gouvernement.
            </li>
            <li>
                <strong>Mobile non couvert en Phase 2A.</strong> Les forfaits mobiles
                seront ajoutés en Phase 2B, avec les données ARCEP de couverture 4G/5G
                qui leur donnent du sens (un forfait mobile sans info couverture est
                de peu d'utilité).
            </li>
            <li>
                <strong>Historique de prix actuellement reconstitué.</strong> La collecte
                automatisée a démarré le 26 avril 2026. Les graphiques affichés sur
                les fiches détail sont marqués comme « démonstration » jusqu'à ce que
                la majorité des points soient des relevés réels (mai 2026 au plus tard).
            </li>
            <li>
                <strong>Score sur dimensions tarif/technique uniquement.</strong> Le score
                ne tient pas compte de la qualité du service après-vente, du temps
                d'attente client, des litiges connus avec un opérateur, ni de la
                qualité réseau réelle (cette dernière sera ajoutée en Phase 2B
                via les données ARCEP).
            </li>
        </ul>
    </section>

    <section class="about-section" id="about">
        <h2 class="t-h1 about-section__title">À propos du projet</h2>
        <p>
            Ce comparateur est un <strong>projet de master</strong> qui démontre un
            pipeline data complet : scraping Python des pages opérateurs, modélisation
            relationnelle MySQL, exposition via une API REST Flask, et frontend PHP.
            Le code source est ouvert et auditable.
        </p>
        <p>
            <strong>Stack technique</strong> — Python 3.12 (scraping + Flask),
            MySQL 8 (MAMP en développement, Docker prévu en Phase 2C),
            PHP 8 (front sans framework), Chart.js (graphique d'évolution
            de prix).
        </p>
        <p>
            Code source :
            <a href="https://github.com/Bastagas/telecom-comparator-fr"
               target="_blank" rel="noopener noreferrer">github.com/Bastagas/telecom-comparator-fr&nbsp;↗</a>
        </p>
        <p class="about-meta">
            Dernière mise à jour des données :
            <strong><?= e((string)$lastUpdate) ?></strong>.
            Cette page documentaire est mise à jour à chaque évolution de la
            méthodologie (recalibrage Phase 2B prévu).
        </p>
    </section>

<?php require __DIR__ . '/partials/footer.php'; ?>
