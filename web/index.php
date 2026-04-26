<?php
/**
 * Placeholder Phase 1.
 *
 * L'écran d'accueil (index.php) sera implémenté en Phase 2 quand on aura
 * les autres écrans (offer.php, about.php). Pour l'instant on redirige
 * vers results.php qui est le seul écran livré du walking skeleton.
 */
declare(strict_types=1);

header('Location: results.php', true, 302);
exit;
