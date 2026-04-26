<?php
/**
 * En-tête HTML commun à toutes les pages PHP.
 * Variables d'entrée optionnelles (à définir avant l'include) :
 *   - $pageTitle (string) : titre de la page (<title>)
 */
declare(strict_types=1);
$pageTitle = $pageTitle ?? 'Comparateur télécom FR';
?><!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title><?= htmlspecialchars($pageTitle, ENT_QUOTES, 'UTF-8') ?></title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="assets/css/tokens.css">
<link rel="stylesheet" href="assets/css/components.css">
<link rel="stylesheet" href="assets/css/layout.css">
</head>
<body>
