-- =====================================================================
-- Migration 2B.1.1bis — Suppression doublon coverage_fibre.locaux_total
-- Date : 2026-04-26
--
-- Décision arbitrée : la donnée "nombre total de locaux dans la commune"
-- est une dimension géographique (propre à la commune) et appartient
-- donc à `communes.locaux_total`. La conserver en doublon dans
-- `coverage_fibre.locaux_total` créerait un risque de désynchronisation
-- à chaque réimport ARCEP.
--
-- coverage_fibre est vide (aucun import effectué), donc le DROP est
-- sans perte de données.
-- =====================================================================

ALTER TABLE coverage_fibre
  DROP COLUMN locaux_total;
