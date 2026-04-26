"""Import de la couverture fibre par commune depuis le CSV ARCEP.

Source : même fichier que `communes.py` (Relevé géographique - données
sous-jacentes ARCEP, millésime 2025-T4). Le cache disque est partagé
avec l'import communes — pas de re-téléchargement.

Mapping ARCEP → coverage_fibre (Phase 2B.1, granularité agrégée) :
  - INSEE_COM         → code_insee
  - operator_id       → NULL (granularité agrégée tous opérateurs)
  - deploye_commune   → locaux_raccordables_ftth (NULL si NA)
  - taux_depl_commune → taux_fibre (multiplié par 100, ratio→%)
  - source_millesime  = '2025_T4' (constante)
  - source_url        = URL du CSV (constante)

Champs laissés NULL pour 2B.1 :
  - locaux_raccordables_thd : nécessite un autre fichier ARCEP
    (distinguant FTTH pur / DOCSIS / autres ≥100 Mb/s).
  - locaux_eligibles_total : idem.

Justification du choix `deploye_commune` plutôt que `IPE_commune`
pour `locaux_raccordables_ftth` :
  - `deploye_commune` mesure les locaux **effectivement raccordables**
    (prise FTTH posée et activable par les FAI commerciaux). C'est la
    mesure officielle ARCEP de la couverture FTTH.
  - `IPE_commune` est un signal d'intention publié par l'OI en avance
    via la procédure IPE (délibération ARCEP 2014-1338) — il englobe
    des locaux à venir, pas encore activables.
  - Aligné numériquement avec `taux_depl_commune` (qui utilise
    deploye / locaux). Cohérence interne BDD préservée.

CLI : `python -m scraper.loader.coverage_fibre`
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path
from typing import Any, Iterator

from scraper.db import get_connection
from scraper.loader.communes import (
    ARCEP_DATASET_URL,
    ARCEP_MILLESIME,
    download_communes,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parsing CSV
# ---------------------------------------------------------------------------

def _parse_int_or_none(raw: str) -> int | None:
    if not raw or raw.strip() in {"", "NA"}:
        return None
    try:
        return int(float(raw.replace(",", ".")))
    except (ValueError, TypeError):
        logger.warning("Cannot parse int value: %r", raw)
        return None


def _parse_taux_fibre(raw: str) -> float | None:
    """Convertit le ratio 0–1 ARCEP en pourcentage 0–100 sur 2 décimales.

    Format ARCEP : "0,936666666666666989" (virgule décimale française).
    Stockage : DECIMAL(5,2), donc max 999.99 ; on round à 2 décimales.
    """
    if not raw or raw.strip() in {"", "NA"}:
        return None
    try:
        ratio = float(raw.replace(",", "."))
        return round(ratio * 100, 2)
    except (ValueError, TypeError):
        logger.warning("Cannot parse taux value: %r", raw)
        return None


def parse_coverage_csv(filepath: Path, source_url: str) -> Iterator[dict[str, Any]]:
    """Itère sur le CSV ARCEP et yield un dict par commune éligible.

    Les communes pour lesquelles AUCUNE donnée fibre n'est disponible
    (taux_depl_commune en NA et deploye_commune en NA simultanément)
    sont skippées — pas de ligne en BDD pour elles. En pratique sur le
    millésime T4 2025 : 0 commune est dans ce cas (taux_depl_commune
    est numérique pour 100 % des lignes).
    """
    with filepath.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row in reader:
            code_insee = (row.get("INSEE_COM") or "").strip()
            if not code_insee:
                continue

            taux = _parse_taux_fibre(row.get("taux_depl_commune") or "")
            deploye = _parse_int_or_none(row.get("deploye_commune") or "")

            # Si aucune donnée fibre → skip cette commune (pas de ligne).
            if taux is None and deploye is None:
                continue

            yield {
                "code_insee": code_insee,
                "locaux_raccordables_ftth": deploye,
                "taux_fibre": taux,
                "source_millesime": ARCEP_MILLESIME,
                "source_url": source_url,
            }


# ---------------------------------------------------------------------------
# Upsert BDD
# ---------------------------------------------------------------------------

UPSERT_SQL = """
INSERT INTO coverage_fibre
  (code_insee, operator_id, locaux_raccordables_ftth, taux_fibre,
   source_millesime, source_url)
VALUES
  (%(code_insee)s, NULL, %(locaux_raccordables_ftth)s, %(taux_fibre)s,
   %(source_millesime)s, %(source_url)s)
ON DUPLICATE KEY UPDATE
  locaux_raccordables_ftth = VALUES(locaux_raccordables_ftth),
  taux_fibre               = VALUES(taux_fibre),
  source_url               = VALUES(source_url)
"""


def upsert_coverage_fibre(cursor, coverage: dict[str, Any]) -> str:
    """Insert ou update une ligne coverage_fibre. Retourne 'inserted' ou 'updated'.

    Match sur la UNIQUE KEY (code_insee, operator_id_key, source_millesime).
    operator_id reste NULL ; operator_id_key (generated stored) vaut 0
    pour tous les enregistrements 2B.1, donc pas de conflit entre lignes.
    """
    cursor.execute(UPSERT_SQL, coverage)
    return "inserted" if cursor.rowcount == 1 else "updated"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _check_communes_loaded(connection, min_count: int = 34000) -> None:
    """Pre-flight : refuse de tourner si la table communes est insuffisamment peuplée."""
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM communes")
        (n,) = cursor.fetchone()
    finally:
        cursor.close()
    if n < min_count:
        raise RuntimeError(
            f"communes table has only {n} rows (< {min_count} expected). "
            "Run `python -m scraper.loader.communes` first."
        )
    logger.info("Pre-flight: %d communes already in DB", n)


def import_coverage_fibre(connection, source_url: str = ARCEP_DATASET_URL) -> dict[str, int]:
    """Pipeline d'import complet."""
    _check_communes_loaded(connection)
    csv_path = download_communes(source_url)

    stats = {"inserted": 0, "updated": 0, "errors": 0, "skipped": 0}
    cursor = connection.cursor()
    batch_size = 1000
    processed = 0

    try:
        for coverage in parse_coverage_csv(csv_path, source_url):
            try:
                kind = upsert_coverage_fibre(cursor, coverage)
                stats[kind] += 1
            except Exception as e:
                stats["errors"] += 1
                logger.warning(
                    "Upsert failed for %s: %s",
                    coverage.get("code_insee"), e,
                )

            processed += 1
            if processed % batch_size == 0:
                connection.commit()
                logger.info(
                    "Processed %d rows (inserted=%d updated=%d errors=%d)",
                    processed, stats["inserted"], stats["updated"], stats["errors"],
                )
        connection.commit()
    finally:
        cursor.close()

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    conn = get_connection()
    try:
        stats = import_coverage_fibre(conn)
    finally:
        conn.close()

    total = stats["inserted"] + stats["updated"]
    logger.info(
        "Done: %d coverage rows processed (inserted=%d, updated=%d, errors=%d, skipped=%d)",
        total, stats["inserted"], stats["updated"], stats["errors"], stats["skipped"],
    )
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
