"""API Flask — Phase 2A endpoints enrichis.

Endpoints :
- GET /api/operators    liste des opérateurs
- GET /api/offers       liste filtrée + paginée
- GET /api/offers/<id>  détail d'une offre
"""

from __future__ import annotations

import math
import os

from flask import Flask, jsonify, request

from api.db import get_connection

app = Flask(__name__)

# Whitelist des tris autorisés (équivalent results.php).
SORT_OPTIONS = {
    "score":      "ORDER BY (o.score IS NULL), o.score DESC, o.monthly_price ASC",
    "price_asc":  "ORDER BY o.monthly_price ASC",
    "price_desc": "ORDER BY o.monthly_price DESC",
}

ALLOWED_TYPES = {"fibre", "mobile", "bundle"}
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def _to_float(value):
    return float(value) if value is not None else None


def _parse_offer_filters(args):
    """Lit et nettoie les query params de /api/offers — version permissive.

    Retourne un dict {operator, type, max_price, min_download, has_promo,
    sort, page, per_page}. Les valeurs invalides sont silencieusement
    coercées vers leur défaut. La validation stricte (400 errors) est
    introduite dans une étape ultérieure.
    """
    operator = args.get("operator") or None
    type_ = args.get("type") if args.get("type") in ALLOWED_TYPES else None

    try:
        max_price = float(args["max_price"]) if args.get("max_price") else None
    except (ValueError, TypeError):
        max_price = None

    try:
        min_download = int(args["min_download"]) if args.get("min_download") else None
    except (ValueError, TypeError):
        min_download = None

    has_promo = args.get("has_promo") == "1"

    sort = args.get("sort") if args.get("sort") in SORT_OPTIONS else "score"

    try:
        page = max(1, int(args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = int(args.get("per_page", DEFAULT_PER_PAGE))
    except (ValueError, TypeError):
        per_page = DEFAULT_PER_PAGE
    per_page = max(1, min(per_page, MAX_PER_PAGE))

    return {
        "operator":     operator,
        "type":         type_,
        "max_price":    max_price,
        "min_download": min_download,
        "has_promo":    has_promo,
        "sort":         sort,
        "page":         page,
        "per_page":     per_page,
    }


def _build_where(filters):
    """Construit la clause WHERE et le dict de bindings depuis les filtres."""
    where = ["o.is_active = TRUE"]
    params = {}

    if filters["operator"]:
        where.append("op.slug = %(operator)s")
        params["operator"] = filters["operator"]
    if filters["type"]:
        where.append("o.type = %(type)s")
        params["type"] = filters["type"]
    if filters["max_price"] is not None:
        where.append("o.monthly_price <= %(max_price)s")
        params["max_price"] = filters["max_price"]
    if filters["min_download"] is not None:
        where.append("fs.download_mbps >= %(min_download)s")
        params["min_download"] = filters["min_download"]
    if filters["has_promo"]:
        where.append("o.promo_price IS NOT NULL")

    return " AND ".join(where), params


@app.get("/api/operators")
def list_operators():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, slug, name, website_url FROM operators ORDER BY name"
        )
        rows = cursor.fetchall()
    finally:
        conn.close()
    return jsonify(rows)


@app.get("/api/offers")
def list_offers():
    filters = _parse_offer_filters(request.args)
    where_sql, params = _build_where(filters)
    order_by = SORT_OPTIONS[filters["sort"]]
    offset = (filters["page"] - 1) * filters["per_page"]

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM offers o
            JOIN operators op ON op.id = o.operator_id
            LEFT JOIN fibre_specs fs ON fs.offer_id = o.id
            WHERE {where_sql}
            """,
            params,
        )
        total = int(cursor.fetchone()["COUNT(*)"])

        page_params = {
            **params,
            "limit": filters["per_page"],
            "offset": offset,
        }
        cursor.execute(
            f"""
            SELECT
                o.id, o.type, o.name,
                o.monthly_price, o.promo_price, o.promo_duration_months,
                o.commitment_months, o.score, o.source_url,
                op.slug AS operator_slug, op.name AS operator_name
            FROM offers o
            JOIN operators op ON op.id = o.operator_id
            LEFT JOIN fibre_specs fs ON fs.offer_id = o.id
            WHERE {where_sql}
            {order_by}
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            page_params,
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    data = [
        {
            "id": row["id"],
            "operator": {
                "slug": row["operator_slug"],
                "name": row["operator_name"],
            },
            "type": row["type"],
            "name": row["name"],
            "monthly_price":         _to_float(row["monthly_price"]),
            "promo_price":           _to_float(row["promo_price"]),
            "promo_duration_months": row["promo_duration_months"],
            "commitment_months":     row["commitment_months"],
            "score":                 _to_float(row["score"]),
            "source_url":            row["source_url"],
        }
        for row in rows
    ]

    total_pages = max(1, math.ceil(total / filters["per_page"]))

    return jsonify({
        "data": data,
        "pagination": {
            "page":        filters["page"],
            "per_page":    filters["per_page"],
            "total":       total,
            "total_pages": total_pages,
        },
        "filters_applied": {
            "operator":     filters["operator"],
            "type":         filters["type"],
            "max_price":    filters["max_price"],
            "min_download": filters["min_download"],
            "has_promo":    filters["has_promo"] or None,
            "sort":         filters["sort"],
        },
    })


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
