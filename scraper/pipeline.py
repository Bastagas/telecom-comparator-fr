"""Orchestrateur du pipeline de scraping.

Phase 1 : appelle uniquement le scraper Free.
Phase 2 : itèrera sur tous les opérateurs + enrichers ARCEP.
"""

from __future__ import annotations

import logging
import sys

from scraper.operators import free

logger = logging.getLogger(__name__)


def run() -> int:
    failures = 0
    for module in (free,):
        name = module.__name__
        try:
            offer_id = module.scrape()
            logger.info("[%s] OK — offer_id=%s", name, offer_id)
        except Exception as exc:
            failures += 1
            logger.exception("[%s] échec : %s", name, exc)
    return failures


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    sys.exit(run())
