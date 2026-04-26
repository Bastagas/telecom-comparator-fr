"""Connexion MySQL et helpers d'upsert pour le pipeline scraping."""

from __future__ import annotations

import logging
import os
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


def upsert_offer(
    operator_slug: str,
    offer: dict[str, Any],
    fibre_specs: dict[str, Any] | None = None,
) -> int:
    """Insert ou met à jour une offre + ses fibre_specs de manière atomique.

    L'upsert s'appuie sur la UNIQUE KEY (operator_id, type, name) de offers.
    Retourne l'id de la ligne offers concernée.
    """
    conn = get_connection()
    conn.autocommit = False
    try:
        cursor = conn.cursor()
        operator_id = get_operator_id(cursor, operator_slug)

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

        conn.commit()
        logger.info("Upserted offer id=%s name=%r", offer_id, offer["name"])
        return offer_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
