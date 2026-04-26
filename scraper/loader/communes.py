"""Import du référentiel communes depuis le CSV ARCEP.

Source : data.gouv.fr — dataset *Le marché du haut et très haut débit fixe
(déploiements)*, fichier *Relevé géographique - données sous-jacentes*
(mise à jour trimestrielle, licence Ouverte).

Le CSV ARCEP fournit code INSEE, nom, code département, code région et
nombre total de locaux par commune. Il ne fournit ni code postal, ni
population, ni coordonnées GPS — ces champs restent NULL pour 2B.1.2 et
pourront être enrichis en Phase 3 via l'API BAN ou un référentiel INSEE
séparé.

CLI : `python -m scraper.loader.communes`
"""

from __future__ import annotations

import csv
import logging
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import requests

from scraper.db import get_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes ARCEP / INSEE
# ---------------------------------------------------------------------------

ARCEP_DATASET_URL = (
    "https://static.data.gouv.fr/resources/"
    "le-marche-du-haut-et-tres-haut-debit-fixe-deploiements/"
    "20260331-154839/releve-geographique-donnees-2026-03.csv"
)

ARCEP_MILLESIME = "2025_T4"

CACHE_DIR = Path.home() / ".cache" / "telecom-comparator" / "arcep"
CACHE_TTL_DAYS = 7

# Table de correspondance code INSEE région → nom officiel.
# La liste des 18 régions françaises est figée depuis la réforme
# territoriale de 2016 (loi NOTRe), donc le hardcodage est acceptable.
# Les codes 07 et 08 sont propres au schéma ARCEP pour Saint-Barthélemy
# et Saint-Martin (qui sont officiellement des Collectivités d'Outre-Mer
# et n'ont pas de code région INSEE standard) — on les nomme
# explicitement pour respecter la donnée publiée.
INSEE_REGION_NAMES: dict[str, str] = {
    "01": "Guadeloupe",
    "02": "Martinique",
    "03": "Guyane",
    "04": "La Réunion",
    "06": "Mayotte",
    "07": "Saint-Barthélemy",
    "08": "Saint-Martin",
    "11": "Île-de-France",
    "24": "Centre-Val de Loire",
    "27": "Bourgogne-Franche-Comté",
    "28": "Normandie",
    "32": "Hauts-de-France",
    "44": "Grand Est",
    "52": "Pays de la Loire",
    "53": "Bretagne",
    "75": "Nouvelle-Aquitaine",
    "76": "Occitanie",
    "84": "Auvergne-Rhône-Alpes",
    "93": "Provence-Alpes-Côte d'Azur",
    "94": "Corse",
}


# ---------------------------------------------------------------------------
# Téléchargement avec cache disque
# ---------------------------------------------------------------------------

def download_communes(url: str, cache_dir: Path = CACHE_DIR) -> Path:
    """Télécharge le CSV ARCEP avec cache disque (TTL 7 jours).

    Le fichier source pèse ~6 MB, mais re-télécharger à chaque run est
    inutile entre deux trimestres ARCEP. Le cache évite la latence et
    le bruit réseau pendant les itérations de dev.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = url.rsplit("/", 1)[-1]
    cached = cache_dir / filename

    if cached.exists():
        age_days = (time.time() - cached.stat().st_mtime) / 86400
        if age_days < CACHE_TTL_DAYS:
            logger.info("Using cached CSV (%s, %.1f days old)", cached, age_days)
            return cached

    logger.info("Downloading %s", url)
    r = requests.get(url, timeout=60, stream=True)
    r.raise_for_status()
    with cached.open("wb") as fh:
        for chunk in r.iter_content(chunk_size=64 * 1024):
            fh.write(chunk)
    logger.info("Downloaded %d bytes to %s", cached.stat().st_size, cached)
    return cached


# ---------------------------------------------------------------------------
# Parsing CSV
# ---------------------------------------------------------------------------

def _parse_locaux(raw: str) -> int | None:
    """Convertit le format français scientifique → int.

    Exemples ARCEP :
      "1,77688663801562e+03" → 1777
      "126362"               → 126362
      ""                     → None
      "NA"                   → None

    La fractionnalité est un artefact statistique ARCEP (probablement
    une pondération inter-trimestres) — on round à l'int parce que
    `communes.locaux_total` est INT et que l'unité métier "1 local" ne
    se prête pas à la décimale.
    """
    if not raw or raw.strip() in {"", "NA"}:
        return None
    try:
        return round(float(raw.replace(",", ".")))
    except (ValueError, TypeError):
        logger.warning("Cannot parse locaux value: %r", raw)
        return None


def parse_communes_csv(filepath: Path) -> Iterator[dict[str, Any]]:
    """Itère sur le CSV ARCEP et yield un dict par commune.

    Les champs absents du CSV (postal_code, population, lat, lng) sont
    retournés implicitement comme None — le caller décide quoi faire.
    """
    unknown_regions: set[str] = set()

    with filepath.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row in reader:
            code_insee = (row.get("INSEE_COM") or "").strip()
            name = (row.get("commune") or "").strip()
            department = (row.get("INSEE_DEP") or "").strip()
            region_code = (row.get("INSEE_REG") or "").strip()
            locaux_total = _parse_locaux(row.get("locaux_commune") or "")

            if not code_insee or not name or not department:
                logger.warning("Skipping row with missing required fields: %r", row)
                continue

            region_name = INSEE_REGION_NAMES.get(region_code)
            if region_code and region_name is None and region_code not in unknown_regions:
                unknown_regions.add(region_code)
                logger.warning(
                    "Unknown INSEE_REG code %r (commune %s — %s); region left NULL",
                    region_code, code_insee, name,
                )

            yield {
                "code_insee": code_insee,
                "name": name,
                "department": department,
                "region": region_name,
                "locaux_total": locaux_total,
            }


# ---------------------------------------------------------------------------
# Upsert BDD
# ---------------------------------------------------------------------------

UPSERT_SQL = """
INSERT INTO communes (code_insee, name, department, region, locaux_total)
VALUES (%(code_insee)s, %(name)s, %(department)s, %(region)s, %(locaux_total)s)
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  department = VALUES(department),
  region = VALUES(region),
  locaux_total = VALUES(locaux_total)
"""


def upsert_commune(cursor, commune: dict[str, Any]) -> str:
    """Insert ou update une commune. Retourne 'inserted' ou 'updated'.

    MySQL renvoie rowcount=1 pour un INSERT, 2 pour un UPDATE via
    ON DUPLICATE KEY (et 0 si la ligne existe déjà avec exactement les
    mêmes valeurs — qu'on traite alors comme un 'updated' silencieux).
    """
    cursor.execute(UPSERT_SQL, commune)
    return "inserted" if cursor.rowcount == 1 else "updated"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def import_communes(connection, source_url: str = ARCEP_DATASET_URL) -> dict[str, int]:
    """Pipeline d'import complet. Retourne un dict de stats."""
    csv_path = download_communes(source_url)

    stats = {"inserted": 0, "updated": 0, "errors": 0, "skipped": 0}
    cursor = connection.cursor()

    batch_size = 1000
    processed = 0

    try:
        for commune in parse_communes_csv(csv_path):
            try:
                kind = upsert_commune(cursor, commune)
                stats[kind] += 1
            except Exception as e:
                stats["errors"] += 1
                logger.warning(
                    "Upsert failed for %s (%s): %s",
                    commune.get("code_insee"), commune.get("name"), e,
                )

            processed += 1
            if processed % batch_size == 0:
                connection.commit()
                logger.info(
                    "Processed %d communes (inserted=%d updated=%d errors=%d)",
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
        stats = import_communes(conn)
    finally:
        conn.close()

    total = stats["inserted"] + stats["updated"]
    logger.info(
        "Done: %d communes processed (inserted=%d, updated=%d, errors=%d, skipped=%d)",
        total, stats["inserted"], stats["updated"], stats["errors"], stats["skipped"],
    )
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
