"""Orchestrateur du pipeline de scraping.

Itère sur la liste des classes d'opérateurs (sous-classes de BaseScraper)
et instancie chacune. Chaque scraper qui échoue est loggé mais ne casse
pas l'exécution des autres (cf. BaseScraper.run).

Code de retour :
- 0 si tous les opérateurs ont upserté au moins une offre.
- N > 0 = nombre d'opérateurs qui n'ont produit aucune offre (utile pour
  cron ou monitoring en Phase 2C).
"""

from __future__ import annotations

import logging
import sys

from scraper.db import get_connection
from scraper.operators.base import BaseScraper
from scraper.operators.bouygues import BouyguesScraper
from scraper.operators.free import FreeScraper
from scraper.operators.orange import OrangeScraper
from scraper.operators.sfr import SfrScraper
from scraper.scoring import recalculate_all_scores

logger = logging.getLogger(__name__)

OPERATORS: list[type[BaseScraper]] = [
    FreeScraper,
    SfrScraper,
    BouyguesScraper,
    OrangeScraper,
]


def run() -> int:
    failures = 0
    total_offers = 0

    for scraper_cls in OPERATORS:
        upserted = scraper_cls().run()
        total_offers += upserted
        if upserted == 0:
            failures += 1

    # Score composite recalculé une fois sur l'ensemble des offres actives.
    # Les stats de marché (min/max) dépendent de toutes les offres : on ne
    # peut donc pas calculer le score offre par offre dans BaseScraper.run.
    conn = get_connection()
    try:
        scored = recalculate_all_scores(conn)
        logger.info("Recalculated scores for %d offer%s", scored, "s" if scored > 1 else "")
    finally:
        conn.close()

    logger.info(
        "Pipeline complete: %d operator%s run, %d offer%s upserted, %d failure%s",
        len(OPERATORS), "s" if len(OPERATORS) > 1 else "",
        total_offers, "s" if total_offers > 1 else "",
        failures, "s" if failures > 1 else "",
    )
    return failures


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    sys.exit(run())
