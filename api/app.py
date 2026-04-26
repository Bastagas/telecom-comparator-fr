"""API Flask — Phase 1 walking skeleton.

Endpoints :
- GET /api/offers       liste simple
- GET /api/offers/<id>  détail d'une offre
"""

from __future__ import annotations

import os

from flask import Flask, jsonify

from api.db import get_connection

app = Flask(__name__)


def _to_float(value):
    return float(value) if value is not None else None


@app.get("/api/offers")
def list_offers():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                o.id,
                op.name AS operator,
                o.type,
                o.name,
                o.monthly_price,
                o.promo_price,
                o.score
            FROM offers o
            JOIN operators op ON op.id = o.operator_id
            WHERE o.is_active = TRUE
            ORDER BY o.id
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    for row in rows:
        row["monthly_price"] = _to_float(row["monthly_price"])
        row["promo_price"] = _to_float(row["promo_price"])
        row["score"] = _to_float(row["score"])

    return jsonify(rows)


@app.get("/api/offers/<int:offer_id>")
def get_offer(offer_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                o.id, o.type, o.name,
                o.monthly_price, o.promo_price, o.promo_duration_months,
                o.commitment_months, o.setup_fee, o.source_url, o.score,
                o.last_scraped_at,
                op.id AS operator_id, op.name AS operator_name,
                op.slug AS operator_slug, op.website_url AS operator_website
            FROM offers o
            JOIN operators op ON op.id = o.operator_id
            WHERE o.id = %s AND o.is_active = TRUE
            """,
            (offer_id,),
        )
        offer = cursor.fetchone()
        if offer is None:
            return jsonify({"error": "Offer not found"}), 404

        specs: dict = {}
        if offer["type"] in ("fibre", "bundle"):
            cursor.execute(
                """
                SELECT download_mbps, upload_mbps, technology, wifi_standard,
                       has_tv, tv_channels_count, has_landline
                FROM fibre_specs WHERE offer_id = %s
                """,
                (offer_id,),
            )
            fibre = cursor.fetchone()
            if fibre:
                fibre["has_tv"] = bool(fibre["has_tv"])
                fibre["has_landline"] = bool(fibre["has_landline"])
                specs["fibre"] = fibre

        if offer["type"] in ("mobile", "bundle"):
            cursor.execute(
                """
                SELECT data_gb_france, data_gb_eu, network_5g,
                       calls_unlimited, sms_unlimited
                FROM mobile_specs WHERE offer_id = %s
                """,
                (offer_id,),
            )
            mobile = cursor.fetchone()
            if mobile:
                mobile["network_5g"] = bool(mobile["network_5g"])
                mobile["calls_unlimited"] = bool(mobile["calls_unlimited"])
                mobile["sms_unlimited"] = bool(mobile["sms_unlimited"])
                specs["mobile"] = mobile

        cursor.execute(
            """
            SELECT opt.name, opt.category, oo.is_included, oo.extra_price
            FROM offer_options oo
            JOIN options opt ON opt.id = oo.option_id
            WHERE oo.offer_id = %s
            ORDER BY opt.id
            """,
            (offer_id,),
        )
        options = cursor.fetchall()
    finally:
        conn.close()

    response = {
        "id": offer["id"],
        "operator": {
            "id": offer["operator_id"],
            "name": offer["operator_name"],
            "slug": offer["operator_slug"],
            "website_url": offer["operator_website"],
        },
        "type": offer["type"],
        "name": offer["name"],
        "pricing": {
            "monthly": _to_float(offer["monthly_price"]),
            "promo": _to_float(offer["promo_price"]),
            "promo_duration_months": offer["promo_duration_months"],
            "commitment_months": offer["commitment_months"],
            "setup_fee": _to_float(offer["setup_fee"]),
        },
        "specs": specs,
        "options": [
            {
                "name": opt["name"],
                "category": opt["category"],
                "is_included": bool(opt["is_included"]),
                "extra_price": _to_float(opt["extra_price"]),
            }
            for opt in options
        ],
        "source_url": offer["source_url"],
        "score": _to_float(offer["score"]),
        "last_scraped_at": offer["last_scraped_at"].isoformat() if offer["last_scraped_at"] else None,
    }
    return jsonify(response)


if __name__ == "__main__":
    # Port 5001 par défaut : sur macOS Monterey+, le port 5000 est squatté
    # par l'AirPlay Receiver (process ControlCenter).
    port = int(os.getenv("API_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=True)
