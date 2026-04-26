"""Connexion MySQL et helper d'upsert pour le pipeline scraping."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import mysql.connector
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )


def get_operator_id(cursor, slug: str) -> int:
    cursor.execute("SELECT id FROM operators WHERE slug = %s", (slug,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Operator not found for slug={slug!r}")
    return row[0]


def upsert_offer(offer: dict[str, Any]) -> int:
    """Insert ou met à jour une offre + ses fibre_specs de manière atomique.

    Le format du dict est défini par `scraper.operators.base` :
        - operator_slug, type, name, monthly_price, promo_price,
          promo_duration_months, commitment_months, setup_fee,
          source_url, score
        - fibre_specs (dict imbriqué) : download_mbps, upload_mbps,
          technology, wifi_standard, has_tv, tv_channels_count, has_landline.
          Peut être absent ou None pour les offres mobile pures.

    L'upsert s'appuie sur la UNIQUE KEY (operator_id, type, name) de offers.
    Retourne l'id de la ligne offers concernée.
    """
    conn = get_connection()
    conn.autocommit = False
    try:
        cursor = conn.cursor()
        operator_id = get_operator_id(cursor, offer["operator_slug"])

        cursor.execute(
            """
            INSERT INTO offers (
                operator_id, type, name, monthly_price, promo_price,
                promo_duration_months, commitment_months, setup_fee,
                source_url, score
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                monthly_price = VALUES(monthly_price),
                promo_price = VALUES(promo_price),
                promo_duration_months = VALUES(promo_duration_months),
                commitment_months = VALUES(commitment_months),
                setup_fee = VALUES(setup_fee),
                source_url = VALUES(source_url),
                score = VALUES(score),
                last_scraped_at = CURRENT_TIMESTAMP
            """,
            (
                operator_id,
                offer["type"],
                offer["name"],
                offer["monthly_price"],
                offer.get("promo_price"),
                offer.get("promo_duration_months"),
                offer.get("commitment_months", 0),
                offer.get("setup_fee", 0),
                offer["source_url"],
                offer.get("score"),
            ),
        )

        cursor.execute(
            "SELECT id FROM offers WHERE operator_id = %s AND type = %s AND name = %s",
            (operator_id, offer["type"], offer["name"]),
        )
        offer_id = cursor.fetchone()[0]

        fibre_specs = offer.get("fibre_specs")
        if fibre_specs is not None:
            cursor.execute(
                """
                INSERT INTO fibre_specs (
                    offer_id, download_mbps, upload_mbps, technology,
                    wifi_standard, has_tv, tv_channels_count, has_landline
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    download_mbps = VALUES(download_mbps),
                    upload_mbps = VALUES(upload_mbps),
                    technology = VALUES(technology),
                    wifi_standard = VALUES(wifi_standard),
                    has_tv = VALUES(has_tv),
                    tv_channels_count = VALUES(tv_channels_count),
                    has_landline = VALUES(has_landline)
                """,
                (
                    offer_id,
                    fibre_specs["download_mbps"],
                    fibre_specs["upload_mbps"],
                    fibre_specs["technology"],
                    fibre_specs.get("wifi_standard"),
                    fibre_specs.get("has_tv", False),
                    fibre_specs.get("tv_channels_count"),
                    fibre_specs.get("has_landline", True),
                ),
            )

        # ─── prices_history (collecte réelle, is_simulated = FALSE) ──────
        # On enregistre une ligne si :
        #   (a) aucune ligne n'existe encore pour cette offre, OU
        #   (b) le prix mensuel diffère du dernier point réel, OU
        #   (c) le dernier point réel date de plus de 24h.
        # Les points simulés (seed) sont ignorés dans la condition pour
        # éviter de masquer des changements réels par la démo.
        cursor.execute(
            """
            SELECT monthly_price, captured_at
            FROM prices_history
            WHERE offer_id = %s AND is_simulated = FALSE
            ORDER BY captured_at DESC
            LIMIT 1
            """,
            (offer_id,),
        )
        last_real = cursor.fetchone()
        should_insert = (
            last_real is None
            or float(last_real[0]) != float(offer["monthly_price"])
            or (datetime.now() - last_real[1]).total_seconds() > 24 * 3600
        )
        if should_insert:
            cursor.execute(
                """
                INSERT INTO prices_history (offer_id, monthly_price, is_simulated)
                VALUES (%s, %s, FALSE)
                """,
                (offer_id, offer["monthly_price"]),
            )
            logger.debug("price_history +1 (real) for offer_id=%s", offer_id)

        conn.commit()
        logger.info("Upserted offer id=%s name=%r", offer_id, offer["name"])
        return offer_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
