"""Seed de démonstration pour prices_history.

But — produire un graphique "Évolution du prix" présentable sur offer.php
dès maintenant, le temps que la collecte automatisée (cf. scraper.db.upsert_offer)
accumule assez de points réels pour s'en passer.

Génère 30 entrées rétroactives (J-30 à J-1) par offre active, avec
is_simulated = TRUE. Le prix de base est `monthly_price` actuel, varié de
± 3 % maximum, par "marches" de 3-7 jours (campagnes tarifaires plausibles)
plutôt que du bruit aléatoire désordonné. Le dernier point simulé (J-1)
est calé proche du prix actuel pour assurer la continuité visuelle avec
le point réel d'aujourd'hui.

Idempotence — les points existants `is_simulated = TRUE` sont supprimés
avant ré-insertion. Les points réels (`is_simulated = FALSE`) ne sont
JAMAIS touchés.

Usage : `python -m scraper.seed_price_history`
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal

from scraper.db import get_connection

logger = logging.getLogger(__name__)

DAYS_BACK = 30
MAX_VARIATION_PCT = 0.03   # ± 3 % autour du prix de base
STEP_MIN_DAYS = 3
STEP_MAX_DAYS = 7
RNG_SEED = 42              # déterministe d'un run à l'autre


def _generate_steps(base_price: float, days: int, rng: random.Random) -> list[float]:
    """Construit une série quotidienne par marches de prix plausibles.

    Le prix reste stable pendant `step_len` jours puis change brusquement,
    ce qui imite une vraie campagne tarifaire (hausse/baisse temporaire).
    Le dernier élément est calé proche du prix de base.
    """
    series: list[float] = []
    cursor_day = 0
    while cursor_day < days - 1:
        step_len = rng.randint(STEP_MIN_DAYS, STEP_MAX_DAYS)
        delta_pct = rng.uniform(-MAX_VARIATION_PCT, MAX_VARIATION_PCT)
        price = round(base_price * (1.0 + delta_pct), 2)
        for _ in range(step_len):
            if cursor_day >= days - 1:
                break
            series.append(price)
            cursor_day += 1
    # Dernier point très proche du prix actuel pour la continuité visuelle.
    series.append(round(base_price * (1.0 + rng.uniform(-0.005, 0.005)), 2))
    return series[:days]


def seed() -> int:
    """Régénère les données simulées. Retourne le nombre de lignes insérées."""
    rng = random.Random(RNG_SEED)

    conn = get_connection()
    conn.autocommit = False
    try:
        cursor = conn.cursor(dictionary=True)

        # Purge des anciennes simulations uniquement.
        cursor.execute("DELETE FROM prices_history WHERE is_simulated = TRUE")
        deleted = cursor.rowcount
        logger.info("Deleted %d existing simulated rows", deleted)

        cursor.execute(
            "SELECT id, monthly_price FROM offers WHERE is_active = TRUE ORDER BY id"
        )
        offers = cursor.fetchall()

        now = datetime.now().replace(microsecond=0)
        inserted = 0
        for offer in offers:
            base_price = float(offer["monthly_price"])
            series = _generate_steps(base_price, DAYS_BACK, rng)
            for i, price in enumerate(series):
                # i = 0 → J-DAYS_BACK ; i = DAYS_BACK-1 → J-1
                captured_at = now - timedelta(days=DAYS_BACK - i)
                cursor.execute(
                    """
                    INSERT INTO prices_history
                        (offer_id, monthly_price, captured_at, is_simulated)
                    VALUES (%s, %s, %s, TRUE)
                    """,
                    (offer["id"], Decimal(str(price)), captured_at),
                )
                inserted += 1

        conn.commit()
        logger.info(
            "Generated %d simulated points × %d offers = %d rows",
            DAYS_BACK, len(offers), inserted,
        )
        return inserted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    seed()
