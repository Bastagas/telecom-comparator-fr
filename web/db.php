<?php
/**
 * Connexion BDD pour la couche web PHP.
 *
 * Choix : parser .env maison plutôt que vlucas/phpdotenv via Composer.
 * Raison Phase 1 : éviter d'introduire Composer pour 4 lignes de config
 * que MAMP sait exécuter directement. Si on ajoute des deps PHP en
 * Phase 2 (templates, validation, etc.), on basculera sur Composer et
 * ce parseur disparaîtra.
 *
 * Le .env est mutualisé avec scraper et api (racine du projet).
 */

declare(strict_types=1);

function load_env(string $path): array {
    if (!is_readable($path)) {
        throw new RuntimeException("Fichier .env introuvable : $path");
    }
    $env = [];
    foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#')) {
            continue;
        }
        if (!str_contains($line, '=')) {
            continue;
        }
        [$key, $value] = explode('=', $line, 2);
        $env[trim($key)] = trim($value);
    }
    return $env;
}

function get_pdo(): PDO {
    static $pdo = null;
    if ($pdo !== null) {
        return $pdo;
    }
    $env = load_env(__DIR__ . '/../.env');
    $dsn = sprintf(
        'mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4',
        $env['DB_HOST'],
        $env['DB_PORT'],
        $env['DB_NAME']
    );
    $pdo = new PDO($dsn, $env['DB_USER'], $env['DB_PASSWORD'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    return $pdo;
}
