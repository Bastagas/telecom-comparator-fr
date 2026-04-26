-- =====================================================================
-- Migration 2B.1.1ter — postal_code passe en NULLable sur communes
-- Date : 2026-04-26
--
-- Justification : le CSV ARCEP "Relevé géographique" ne contient pas
-- le code postal des communes. Le code postal est :
--   - non univoque (une commune peut avoir plusieurs CP, ex. arrond.
--     parisiens 75001-75020 vs commune 75056 unique pour Paris)
--   - non nécessaire à la fonction première du comparateur (la clé
--     fonctionnelle est le code INSEE pour la couverture FTTH)
--   - récupérable en Phase 3 via l'API BAN qui renvoie INSEE+CP par
--     adresse, sans qu'on ait à le stocker ici.
-- =====================================================================

ALTER TABLE communes
  MODIFY COLUMN postal_code VARCHAR(5) NULL;
