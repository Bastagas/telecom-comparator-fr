-- =====================================================================
-- Migration 2B.1.1 — Schéma ARCEP fibre + harmonisation timestamps
-- Date : 2026-04-26
--
-- Cette migration prépare l'import du référentiel communes INSEE et
-- des données de couverture FTTH publiées par l'ARCEP (Observatoire du
-- Très Haut Débit, mises à jour trimestrielles).
--
-- Décisions techniques (cf. JOURNAL Tâche 2B.1.1) :
--   1. Naming ARCEP-strict : "raccordables" (FTTH/THD) plutôt que
--      "éligibles" — fidélité documentaire au vocabulaire publié par
--      le régulateur (cf. data.arcep.fr/fixe/maconnexioninternet/).
--   2. DROP des champs redondants : `locaux_raccordables`,
--      `pct_couverture`, `data_source` étaient des placeholders Phase 1
--      remplacés par un design plus expressif.
--   3. RENAME `captured_at → imported_at` sur les 2 tables couverture
--      (fibre + mobile) — sémantique import CSV vs capture scrape.
--      Cohérence cross-table (cf. C dans la discussion 2B.1.1).
--   4. Generated column STORED `operator_id_key = IFNULL(operator_id, 0)`
--      pour contourner le NULL distinct de MySQL dans une UNIQUE KEY,
--      sans casser la sémantique FK NULL = données agrégées.
--   5. Swap FK CASCADE → RESTRICT sur les FK opérateur des 2 tables
--      couverture. Justification double :
--      (a) requis techniquement : MySQL interdit ON DELETE CASCADE sur
--          la base column d'une stored generated column.
--      (b) plus juste sémantiquement : on ne veut pas qu'une suppression
--          accidentelle d'opérateur efface en cascade des centaines de
--          milliers de lignes de couverture. RESTRICT force une
--          suppression explicite, le CASCADE Phase 1 était une posture
--          défensive non justifiée par un cas d'usage réel.
-- =====================================================================

-- ─────────────────────────────────────────────────────────────────────
-- Table communes : enrichissement
-- ─────────────────────────────────────────────────────────────────────
ALTER TABLE communes
  ADD COLUMN locaux_total INT NULL AFTER region,
  ADD COLUMN imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

-- Note : idx_name, idx_postal, idx_department sont déjà présents
-- depuis la création initiale (Phase 1). Pas d'ajout d'index.

-- ─────────────────────────────────────────────────────────────────────
-- Swap FK CASCADE → RESTRICT sur les tables coverage_*
-- (préalable obligatoire au ADD COLUMN STORED ci-dessous, et
--  alignement proactif sur coverage_mobile pour 2B.2)
-- ─────────────────────────────────────────────────────────────────────
ALTER TABLE coverage_fibre
  DROP FOREIGN KEY fk_cf_operator;

ALTER TABLE coverage_fibre
  ADD CONSTRAINT fk_cf_operator FOREIGN KEY (operator_id)
    REFERENCES operators(id) ON DELETE RESTRICT;

ALTER TABLE coverage_mobile
  DROP FOREIGN KEY fk_cm_operator;

ALTER TABLE coverage_mobile
  ADD CONSTRAINT fk_cm_operator FOREIGN KEY (operator_id)
    REFERENCES operators(id) ON DELETE RESTRICT;

-- ─────────────────────────────────────────────────────────────────────
-- Table coverage_fibre : refonte structure
-- ─────────────────────────────────────────────────────────────────────
ALTER TABLE coverage_fibre
  DROP COLUMN locaux_raccordables,
  DROP COLUMN pct_couverture,
  DROP COLUMN data_source,
  CHANGE COLUMN captured_at imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,
  ADD COLUMN locaux_raccordables_ftth INT NULL,
  ADD COLUMN locaux_raccordables_thd INT NULL,
  ADD COLUMN locaux_eligibles_total INT NULL,
  ADD COLUMN taux_fibre DECIMAL(5,2) NULL,
  ADD COLUMN source_millesime VARCHAR(10) NOT NULL DEFAULT '',
  ADD COLUMN source_url TEXT NULL,
  ADD COLUMN operator_id_key INT
    GENERATED ALWAYS AS (IFNULL(operator_id, 0)) STORED NOT NULL,
  ADD UNIQUE KEY uniq_commune_op_millesime
    (code_insee, operator_id_key, source_millesime),
  ADD INDEX idx_taux_fibre (taux_fibre);

-- ─────────────────────────────────────────────────────────────────────
-- Table coverage_mobile : alignement timestamp
-- (refonte complète prévue en 2B.2 quand le mobile entrera en scope)
-- ─────────────────────────────────────────────────────────────────────
ALTER TABLE coverage_mobile
  CHANGE COLUMN captured_at imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;
